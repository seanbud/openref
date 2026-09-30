# This file is part of BeeRef.
#
# BeeRef is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BeeRef is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BeeRef.  If not, see <https://www.gnu.org/licenses/>.

"""Classes for items that are added to the scene by the user (images,
text).
"""

import copy
from collections import defaultdict
from functools import cached_property
from html.parser import HTMLParser
import logging
import math
import os.path
import re

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt

from beeref import commands
from beeref.config import BeeSettings
from beeref.constants import COLORS
from beeref.selection import SelectableMixin


logger = logging.getLogger(__name__)

item_registry = {}


def register_item(cls):
    item_registry[cls.TYPE] = cls
    return cls


def sort_by_filename(items):
    """Order items by filename.

    Items with a filename (ordered by filename) first, then items
    without a filename but with a save_id follow (ordered by
    save_id), then remaining items in the order that they have
    been inserted into the scene.
    """

    items_by_filename = []
    items_by_save_id = []
    items_remaining = []

    for item in items:
        if getattr(item, 'filename', None):
            items_by_filename.append(item)
        elif getattr(item, 'save_id', None):
            items_by_save_id.append(item)
        else:
            items_remaining.append(item)

    items_by_filename.sort(key=lambda x: x.filename)
    items_by_save_id.sort(key=lambda x: x.save_id)
    return items_by_filename + items_by_save_id + items_remaining


class BeeItemMixin(SelectableMixin):
    """Base for all items added by the user."""

    def set_pos_center(self, pos):
        """Sets the position using the item's center as the origin point."""

        self.setPos(pos - self.center_scene_coords)

    def has_selection_outline(self):
        return self.isSelected()

    def has_selection_handles(self):
        return (self.isSelected()
                and self.scene()
                and self.scene().has_single_selection())

    def selection_action_items(self):
        """The items affected by selection actions like scaling and rotating.
        """
        return [self]

    def on_selected_change(self, value):
        # Layer changes are handled by BeeGraphicsScene after mouse
        # selection settles, where they can be recorded in the undo stack.
        # This hook remains for selectable-item compatibility.
        return None

    def update_from_data(self, **kwargs):
        self.save_id = kwargs.get('save_id', self.save_id)
        self.setPos(kwargs.get('x', self.pos().x()),
                    kwargs.get('y', self.pos().y()))
        self.setZValue(kwargs.get('z', self.zValue()))
        self.setScale(kwargs.get('scale', self.scale()))
        self.setRotation(kwargs.get('rotation', self.rotation()))
        if kwargs.get('flip', 1) != self.flip():
            self.do_flip()


@register_item
class BeePixmapItem(BeeItemMixin, QtWidgets.QGraphicsPixmapItem):
    """Class for images added by the user."""

    TYPE = 'pixmap'
    CROP_HANDLE_SIZE = 15

    def __init__(self, image, filename=None, **kwargs):
        super().__init__(QtGui.QPixmap.fromImage(image))
        self.save_id = None
        self.filename = filename
        self.reset_crop()
        logger.debug(f'Initialized {self}')
        self.is_image = True
        self.crop_mode = False
        self.init_selectable()
        self.settings = BeeSettings()
        self.grayscale = False

    @classmethod
    def create_from_data(self, **kwargs):
        item = kwargs.pop('item')
        data = kwargs.pop('data', {})
        item.filename = item.filename or data.get('filename')
        if 'crop' in data:
            item.crop = QtCore.QRectF(*data['crop'])
        item.setOpacity(data.get('opacity', 1))
        item.grayscale = data.get('grayscale', False)
        return item

    def __str__(self):
        size = self.pixmap().size()
        return (f'Image "{self.filename}" {size.width()} x {size.height()}')

    @property
    def crop(self):
        return self._crop

    @crop.setter
    def crop(self, value):
        logger.debug(f'Setting crop for {self} to {value}')
        self.prepareGeometryChange()
        self._crop = value
        self.update()

    @property
    def grayscale(self):
        return self._grayscale

    @grayscale.setter
    def grayscale(self, value):
        logger.debug('Setting grayscale for {self} to {value}')
        self._grayscale = value
        if value is True:
            # Using the grayscale image format to convert to grayscale
            # loses an image's tranparency. So the straightworward
            # following method gives us an ugly black replacement:
            # img = img.convertToFormat(QtGui.QImage.Format.Format_Grayscale8)

            # Instead, we will fill the background with the current
            # canvas colour, so the issue is only visible if the image
            # overlaps other images. The way we do it here only works
            # as long as the canvas colour is itself grayscale,
            # though.
            img = QtGui.QImage(
                self.pixmap().size(), QtGui.QImage.Format.Format_Grayscale8)
            img.fill(QtGui.QColor(*COLORS['Scene:Canvas']))
            painter = QtGui.QPainter(img)
            painter.drawPixmap(0, 0, self.pixmap())
            painter.end()
            self._grayscale_pixmap = QtGui.QPixmap.fromImage(img)

            # Alternative methods that have their own issues:
            #
            # 1. Use setAlphaChannel of the resulting grayscale
            # image. How do we get the original alpha channel? Using
            # the whole original image also takes color values into
            # account, not just their alpha values.
            #
            # 2. QtWidgets.QGraphicsColorizeEffect() with black colour
            # on the GraphicsItem. This applys to everything the paint
            # method does, so the selection outline/handles will also
            # be gray. setGraphicsEffect is only available on some
            # widgets, so we can't apply it selectively.
            #
            # 3. Going through every pixel and doing it manually — bad
            # performance.
        else:
            self._grayscale_pixmap = None

        self.update()

    def sample_color_at(self, pos):
        ipos = self.mapFromScene(pos)
        if self.grayscale:
            pm = self._grayscale_pixmap
        else:
            pm = self.pixmap()
        # Copying one pixel avoids converting a multi-megapixel pixmap for
        # every mouse-move event while the sampler is active.
        x = int(ipos.x())
        y = int(ipos.y())
        if 0 <= x < pm.width() and 0 <= y < pm.height():
            img = pm.copy(x, y, 1, 1).toImage()
            color = img.pixelColor(0, 0)
            if color.alpha():
                return color

    def bounding_rect_unselected(self):
        if self.crop_mode:
            return QtWidgets.QGraphicsPixmapItem.boundingRect(self)
        else:
            return self.crop

    def get_extra_save_data(self):
        return {'filename': self.filename,
                'opacity': self.opacity(),
                'grayscale': self.grayscale,
                'crop': [self.crop.topLeft().x(),
                         self.crop.topLeft().y(),
                         self.crop.width(),
                         self.crop.height()]}

    def get_filename_for_export(self, imgformat, save_id_default=None):
        save_id = self.save_id or save_id_default
        assert save_id is not None

        if self.filename:
            basename = os.path.splitext(os.path.basename(self.filename))[0]
            return f'{save_id:04}-{basename}.{imgformat}'
        else:
            return f'{save_id:04}.{imgformat}'

    def get_imgformat(self, img):
        """Determines the format for storing this image."""

        formt = self.settings.valueOrDefault('Items/image_storage_format')

        if formt == 'best':
            # Images with alpha channel and small images are stored as png
            if (img.hasAlphaChannel()
                    or (img.height() < 500 and img.width() < 500)):
                formt = 'png'
            else:
                formt = 'jpg'

        logger.debug(f'Found format {formt} for {self}')
        return formt

    def pixmap_to_bytes(self, apply_grayscale=False, apply_crop=False):
        """Convert the pixmap data to PNG bytestring."""
        barray = QtCore.QByteArray()
        buffer = QtCore.QBuffer(barray)
        buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
        if apply_grayscale and self.grayscale:
            pm = self._grayscale_pixmap
        else:
            pm = self.pixmap()

        if apply_crop:
            pm = pm.copy(self.crop.toRect())

        img = pm.toImage()
        imgformat = self.get_imgformat(img)
        img.save(buffer, imgformat.upper(), quality=90)
        return (barray.data(), imgformat)

    def setPixmap(self, pixmap):
        super().setPixmap(pixmap)
        self.reset_crop()

    def pixmap_from_bytes(self, data):
        """Set image pimap from a bytestring."""
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(data)
        self.setPixmap(pixmap)

    def create_copy(self):
        item = BeePixmapItem(QtGui.QImage(), self.filename)
        item.setPixmap(self.pixmap())
        item.setPos(self.pos())
        item.setZValue(self.zValue())
        item.setScale(self.scale())
        item.setRotation(self.rotation())
        item.setOpacity(self.opacity())
        item.grayscale = self.grayscale
        if self.flip() == -1:
            item.do_flip()
        item.crop = self.crop
        return item

    @cached_property
    def color_gamut(self):
        logger.debug(f'Calculating color gamut for {self}')
        gamut = defaultdict(int)
        img = self.pixmap().toImage()
        # Don't evaluate every pixel for larger images:
        step = max(1, int(max(img.width(), img.height()) / 1000))
        logger.debug(f'Considering every {step}. row/column')

        # Not actually faster than solution below :(
        # ptr = img.bits()
        # size = img.sizeInBytes()
        # pixelsize = int(img.sizeInBytes() / img.width() / img.height())
        # ptr.setsize(size)
        # for pixel in batched(ptr, n=pixelsize):
        #     r, g, b, alpha = tuple(map(ord, pixel))
        #     if 5 < alpha and 5 < r < 250 and 5 < g < 250 and 5 < b < 250:
        #         # Only consider pixels that aren't close to
        #         # transparent, white or black
        #         rgb = QtGui.QColor(r, g, b)
        #         gamut[rgb.hue(), rgb.saturation()] += 1

        for i in range(0, img.width(), step):
            for j in range(0, img.height(), step):
                rgb = img.pixelColor(i, j)
                rgbtuple = (rgb.red(), rgb.blue(), rgb.green())
                if (5 < rgb.alpha()
                        and min(rgbtuple) < 250 and max(rgbtuple) > 5):
                    # Only consider pixels that aren't close to
                    # transparent, white or black
                    gamut[rgb.hue(), rgb.saturation()] += 1

        logger.debug(f'Got {len(gamut)} color gamut values')
        return gamut

    def copy_to_clipboard(self, clipboard):
        clipboard.setPixmap(self.pixmap())

    def reset_crop(self):
        self.crop = QtCore.QRectF(
            0, 0, self.pixmap().size().width(), self.pixmap().size().height())

    @property
    def crop_handle_size(self):
        return self.fixed_length_for_viewport(self.CROP_HANDLE_SIZE)

    def crop_handle_topleft(self):
        topleft = self.crop_temp.topLeft()
        return QtCore.QRectF(
            topleft.x(),
            topleft.y(),
            self.crop_handle_size,
            self.crop_handle_size)

    def crop_handle_bottomleft(self):
        bottomleft = self.crop_temp.bottomLeft()
        return QtCore.QRectF(
            bottomleft.x(),
            bottomleft.y() - self.crop_handle_size,
            self.crop_handle_size,
            self.crop_handle_size)

    def crop_handle_bottomright(self):
        bottomright = self.crop_temp.bottomRight()
        return QtCore.QRectF(
            bottomright.x() - self.crop_handle_size,
            bottomright.y() - self.crop_handle_size,
            self.crop_handle_size,
            self.crop_handle_size)

    def crop_handle_topright(self):
        topright = self.crop_temp.topRight()
        return QtCore.QRectF(
            topright.x() - self.crop_handle_size,
            topright.y(),
            self.crop_handle_size,
            self.crop_handle_size)

    def crop_handles(self):
        return (self.crop_handle_topleft,
                self.crop_handle_bottomleft,
                self.crop_handle_bottomright,
                self.crop_handle_topright)

    def crop_edge_top(self):
        topleft = self.crop_temp.topLeft()
        return QtCore.QRectF(
            topleft.x() + self.crop_handle_size,
            topleft.y(),
            self.crop_temp.width() - 2 * self.crop_handle_size,
            self.crop_handle_size)

    def crop_edge_left(self):
        topleft = self.crop_temp.topLeft()
        return QtCore.QRectF(
            topleft.x(),
            topleft.y() + self.crop_handle_size,
            self.crop_handle_size,
            self.crop_temp.height() - 2 * self.crop_handle_size)

    def crop_edge_bottom(self):
        bottomleft = self.crop_temp.bottomLeft()
        return QtCore.QRectF(
            bottomleft.x() + self.crop_handle_size,
            bottomleft.y() - self.crop_handle_size,
            self.crop_temp.width() - 2 * self.crop_handle_size,
            self.crop_handle_size)

    def crop_edge_right(self):
        topright = self.crop_temp.topRight()
        return QtCore.QRectF(
            topright.x() - self.crop_handle_size,
            topright.y() + self.crop_handle_size,
            self.crop_handle_size,
            self.crop_temp.height() - 2 * self.crop_handle_size)

    def crop_edges(self):
        return (self.crop_edge_top,
                self.crop_edge_left,
                self.crop_edge_bottom,
                self.crop_edge_right)

    def get_crop_handle_cursor(self, handle):
        """Gets the crop cursor for the given handle."""

        is_topleft_or_bottomright = handle in (
            self.crop_handle_topleft, self.crop_handle_bottomright)
        return self.get_diag_cursor(is_topleft_or_bottomright)

    def get_crop_edge_cursor(self, edge):
        """Gets the crop edge cursor for the given edge."""

        top_or_bottom = edge in (
            self.crop_edge_top, self.crop_edge_bottom)
        sideways = (45 < self.rotation() < 135
                    or 225 < self.rotation() < 315)

        if top_or_bottom is sideways:
            return Qt.CursorShape.SizeHorCursor
        else:
            return Qt.CursorShape.SizeVerCursor

    def draw_crop_rect(self, painter, rect):
        """Paint a dotted rectangle for the cropping UI."""
        pen = QtGui.QPen(QtGui.QColor(255, 255, 255))
        pen.setWidth(2)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.drawRect(rect)
        pen.setColor(QtGui.QColor(0, 0, 0))
        pen.setStyle(Qt.PenStyle.DotLine)
        painter.setPen(pen)
        painter.drawRect(rect)

    def paint(self, painter, option, widget):
        if abs(painter.combinedTransform().m11()) < 2:
            # We want image smoothing, but only for images where we
            # are not zoomed in a lot. This is to ensure that for
            # example icons and pixel sprites can be viewed correctly.
            painter.setRenderHint(painter.RenderHint.SmoothPixmapTransform)

        if self.crop_mode:
            self.paint_debug(painter, option, widget)

            # Darken image outside of cropped area
            painter.drawPixmap(0, 0, self.pixmap())
            path = QtWidgets.QGraphicsPixmapItem.shape(self)
            path.addRect(self.crop_temp)
            color = QtGui.QColor(0, 0, 0)
            color.setAlpha(100)
            painter.setBrush(QtGui.QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(path)
            painter.setBrush(QtGui.QBrush())

            for handle in self.crop_handles():
                self.draw_crop_rect(painter, handle())
            self.draw_crop_rect(painter, self.crop_temp)
        else:
            pm = self._grayscale_pixmap if self.grayscale else self.pixmap()
            painter.drawPixmap(self.crop, pm, self.crop)
            self.paint_selectable(painter, option, widget)

    def enter_crop_mode(self):
        logger.debug(f'Entering crop mode on {self}')
        self.prepareGeometryChange()
        self.crop_mode = True
        self.crop_temp = QtCore.QRectF(self.crop)
        self.crop_mode_move = None
        self.crop_mode_event_start = None
        self.grabKeyboard()
        self.update()
        self.scene().crop_item = self

    def exit_crop_mode(self, confirm):
        logger.debug(f'Exiting crop mode with {confirm} on {self}')
        if confirm and self.crop != self.crop_temp:
            self.scene().undo_stack.push(
                commands.CropItem(self, self.crop_temp))
        self.prepareGeometryChange()
        self.crop_mode = False
        self.crop_temp = None
        self.crop_mode_move = None
        self.crop_mode_event_start = None
        self.ungrabKeyboard()
        self.update()
        self.scene().crop_item = None

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.exit_crop_mode(confirm=True)
        elif event.key() == Qt.Key.Key_Escape:
            self.exit_crop_mode(confirm=False)
        else:
            super().keyPressEvent(event)

    def hoverMoveEvent(self, event):
        if not self.crop_mode:
            return super().hoverMoveEvent(event)

        for handle in self.crop_handles():
            if handle().contains(event.pos()):
                self.set_cursor(self.get_crop_handle_cursor(handle))
                return
        for edge in self.crop_edges():
            if edge().contains(event.pos()):
                self.set_cursor(self.get_crop_edge_cursor(edge))
                return
        self.unset_cursor()

    def mousePressEvent(self, event):
        if not self.crop_mode:
            return super().mousePressEvent(event)

        event.accept()
        for handle in self.crop_handles():
            # Click into a handle?
            if handle().contains(event.pos()):
                self.crop_mode_event_start = event.pos()
                self.crop_mode_move = handle
                return
        for edge in self.crop_edges():
            # Click into an edge handle?
            if edge().contains(event.pos()):
                self.crop_mode_event_start = event.pos()
                self.crop_mode_move = edge
                return
        # Click not in handle, end cropping mode:
        self.exit_crop_mode(
            confirm=self.crop_temp.contains(event.pos()))

    def ensure_point_within_crop_bounds(self, point, handle):
        """Returns the point, or the nearest point within the pixmap."""

        if handle == self.crop_handle_topleft:
            topleft = QtCore.QPointF(0, 0)
            bottomright = self.crop_temp.bottomRight()
        if handle == self.crop_handle_bottomleft:
            topleft = QtCore.QPointF(0, self.crop_temp.top())
            bottomright = QtCore.QPointF(
                self.crop_temp.right(), self.pixmap().size().height())
        if handle == self.crop_handle_bottomright:
            topleft = self.crop_temp.topLeft()
            bottomright = QtCore.QPointF(
                self.pixmap().size().width(), self.pixmap().size().height())
        if handle == self.crop_handle_topright:
            topleft = QtCore.QPointF(self.crop_temp.left(), 0)
            bottomright = QtCore.QPointF(
                self.pixmap().size().width(), self.crop_temp.bottom())
        if handle == self.crop_edge_top:
            topleft = QtCore.QPointF(0, 0)
            bottomright = QtCore.QPointF(
                self.pixmap().size().width(), self.crop_temp.bottom())
        if handle == self.crop_edge_bottom:
            topleft = QtCore.QPointF(0, self.crop_temp.top())
            bottomright = QtCore.QPointF(
                self.pixmap().size().width(), self.pixmap().size().height())
        if handle == self.crop_edge_left:
            topleft = QtCore.QPointF(0, 0)
            bottomright = QtCore.QPointF(
                self.crop_temp.right(), self.pixmap().size().height())
        if handle == self.crop_edge_right:
            topleft = QtCore.QPointF(self.crop_temp.left(), 0)
            bottomright = QtCore.QPointF(
                self.pixmap().size().width(), self.pixmap().size().height())

        point.setX(min(bottomright.x(), max(topleft.x(), point.x())))
        point.setY(min(bottomright.y(), max(topleft.y(), point.y())))

        return point

    def mouseMoveEvent(self, event):
        if self.crop_mode and self.crop_mode_event_start:
            diff = event.pos() - self.crop_mode_event_start
            if self.crop_mode_move == self.crop_handle_topleft:
                new = self.ensure_point_within_crop_bounds(
                    self.crop_temp.topLeft() + diff, self.crop_mode_move)
                self.crop_temp.setTopLeft(new)
            if self.crop_mode_move == self.crop_handle_bottomleft:
                new = self.ensure_point_within_crop_bounds(
                    self.crop_temp.bottomLeft() + diff, self.crop_mode_move)
                self.crop_temp.setBottomLeft(new)
            if self.crop_mode_move == self.crop_handle_bottomright:
                new = self.ensure_point_within_crop_bounds(
                    self.crop_temp.bottomRight() + diff, self.crop_mode_move)
                self.crop_temp.setBottomRight(new)
            if self.crop_mode_move == self.crop_handle_topright:
                new = self.ensure_point_within_crop_bounds(
                    self.crop_temp.topRight() + diff, self.crop_mode_move)
                self.crop_temp.setTopRight(new)
            if self.crop_mode_move == self.crop_edge_top:
                new = self.ensure_point_within_crop_bounds(
                    self.crop_temp.topLeft() + diff, self.crop_mode_move)
                self.crop_temp.setTop(new.y())
            if self.crop_mode_move == self.crop_edge_left:
                new = self.ensure_point_within_crop_bounds(
                    self.crop_temp.topLeft() + diff, self.crop_mode_move)
                self.crop_temp.setLeft(new.x())
            if self.crop_mode_move == self.crop_edge_bottom:
                new = self.ensure_point_within_crop_bounds(
                    self.crop_temp.bottomLeft() + diff, self.crop_mode_move)
                self.crop_temp.setBottom(new.y())
            if self.crop_mode_move == self.crop_edge_right:
                new = self.ensure_point_within_crop_bounds(
                    self.crop_temp.topRight() + diff, self.crop_mode_move)
                self.crop_temp.setRight(new.x())
            self.update()
            self.crop_mode_event_start = event.pos()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.crop_mode:
            self.crop_mode_move = None
            self.crop_mode_event_start = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class _SafeNoteHTML(HTMLParser):
    """Small, deliberately boring HTML allow-list for pasted notes.

    QTextDocument supports images and resource URLs in HTML.  Notes should be
    portable data, not a way to make the canvas retrieve arbitrary resources,
    so images, stylesheets and URL attributes are not copied into the document.
    """

    TAGS = {
        'p', 'br', 'b', 'strong', 'i', 'em', 'u', 's', 'strike', 'code',
        'pre', 'blockquote', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4',
        'h5', 'h6', 'span', 'font', 'a',
    }
    VOID = {'br'}
    UNSAFE_VOID = {'meta', 'link', 'base', 'img', 'source', 'input'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.stack = []
        self.drop_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if self.drop_depth:
            if tag in self.UNSAFE_VOID:
                return
            self.drop_depth += 1
            return
        if tag in {'head', 'style', 'script', 'title', 'iframe', 'object'}:
            self.drop_depth = 1
            return
        if tag not in self.TAGS:
            return
        attrs = dict(attrs)
        # Links retain their readable label only.  Allow a text colour, but no
        # arbitrary CSS (which Qt accepts more broadly than browsers do).
        if tag == 'span':
            style = _safe_css_style(attrs.get('style', ''))
            attrs = {'style': style} if style else {}
        elif tag == 'font':
            color = attrs.get('color')
            attrs = {'color': color} if _valid_color(color) else {}
        else:
            attrs = {}
        attr_text = ''.join(f' {name}="{value}"'
                            for name, value in attrs.items())
        # Attribute values have already been restricted to colours.  Qt's
        # colour grammar contains no quote characters.
        self.parts.append(f'<{tag}{attr_text}>')
        self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.drop_depth:
            self.drop_depth -= 1
            return
        if tag not in self.TAGS or tag not in self.stack:
            return
        # Close nested permitted elements up to the matching tag.  Ignored
        # tags must never affect this stack (e.g. a standalone <img>).
        while self.stack:
            opened = self.stack.pop()
            if opened not in self.VOID:
                self.parts.append(f'</{opened}>')
            if opened == tag:
                break

    def handle_data(self, data):
        if self.drop_depth:
            return
        self.parts.append(data.replace('&', '&amp;').replace('<', '&lt;')
                          .replace('>', '&gt;'))

    def result(self):
        # Close only tags that were actually permitted.  This also makes a
        # malformed clipboard fragment deterministic when serialized later.
        for tag in reversed(self.stack):
            if tag not in self.VOID:
                self.parts.append(f'</{tag}>')
        return ''.join(self.parts)


def _valid_color(value):
    return bool(value) and QtGui.QColor(value).isValid()


def _safe_css_color(style):
    for declaration in style.split(';'):
        name, separator, value = declaration.partition(':')
        if separator and name.strip().lower() == 'color':
            value = value.strip()
            if _valid_color(value):
                return value
    return None


def _safe_css_style(style):
    """Keep the small inline style vocabulary Qt emits for rich notes."""
    permitted = []
    for declaration in style.split(';'):
        name, separator, value = declaration.partition(':')
        name, value = name.strip().lower(), value.strip().lower()
        if not separator:
            continue
        if name == 'color' and _valid_color(value):
            permitted.append(f'color:{value}')
        elif name == 'font-weight' and (value == 'bold' or value.isdigit()):
            permitted.append(f'font-weight:{value}')
        elif name == 'font-style' and value in ('normal', 'italic'):
            permitted.append(f'font-style:{value}')
        elif name == 'text-decoration' and value in (
                'none', 'underline', 'line-through', 'underline line-through'):
            permitted.append(f'text-decoration:{value}')
        elif name == 'font-size' and value.endswith(('px', 'pt')):
            try:
                if float(value[:-2]) > 0:
                    permitted.append(f'font-size:{value}')
            except ValueError:
                pass
        elif name == 'font-family' and any(
                family in value
                for family in ('monospace', 'courier', 'code')):
            # Qt exports code spans as a family style instead of <code>.
            permitted.append('font-family:monospace')
    return ';'.join(permitted)


def _sanitize_note_html(html):
    parser = _SafeNoteHTML()
    parser.feed(html or '')
    parser.close()
    return parser.result()


def _looks_like_markdown(text):
    return bool(re.search(r'(^|\n)(#{1,6}\s|[-*+]\s|\d+[.)]\s)|'
                          r'\*\*.+?\*\*|__.+?__|`[^`]+`', text or ''))


@register_item
class BeeTextItem(BeeItemMixin, QtWidgets.QGraphicsTextItem):
    """An editable note with a durable rich-text representation.

    ``text`` remains the plain-text compatibility field.  New notes also save
    sanitized HTML, dimensions and the card appearance so their document can
    round-trip without depending on Qt's current default style.
    """

    TYPE = 'text'
    DEFAULT_APPEARANCE = {
        # QColor's eight-digit hexadecimal form is #AARRGGBB.
        'fill': '#28000000',
        'border_color': '#00000000',
        'border_width': 0,
        # Match the original text-card treatment. Rich-note appearance is
        # still persisted for existing boards, but a new note should start as
        # the familiar compact square-backed label.
        'radius': 0,
    }

    def __init__(self, text=None, html=None, font_size=None,
                 text_width=None, appearance=None, **kwargs):
        # Keep old construction semantics for code and old files that only
        # supplied a text field.  New-note callers explicitly provide a font
        # size, width and an empty text string.
        legacy = font_size is None and text_width is None and html is None
        super().__init__()
        self.save_id = None
        self.is_image = False
        self.init_selectable()
        self.is_editable = True
        self.edit_mode = False
        self._applying_state = False
        self._font_size = int(font_size) if font_size is not None else None
        self._text_width = float(text_width) if text_width is not None else -1
        self.appearance = dict(self.DEFAULT_APPEARANCE)
        self.appearance.update(appearance or {})
        self._normalize_appearance()
        self.setDefaultTextColor(QtGui.QColor(*COLORS['Scene:Text']))
        self.document().contentsChanged.connect(self._document_changed)
        if self._font_size is not None:
            self._set_default_font_size(self._font_size)
        self.setTextWidth(self._text_width)
        if html is not None:
            self.document().setHtml(_sanitize_note_html(html))
        else:
            initial_text = 'Text' if text is None and legacy else text
            self.setPlainText(initial_text or '')
        logger.debug(f'Initialized {self}')

    @classmethod
    def create_from_data(cls, **kwargs):
        return cls(**kwargs.get('data', {}))

    def __str__(self):
        return f'Text "{self.toPlainText()[:40]}"'

    @property
    def font_size(self):
        return self._font_size

    @property
    def text_width(self):
        return self._text_width

    def _normalize_appearance(self):
        self.appearance = self._normalized_appearance(self.appearance)

    @classmethod
    def _normalized_appearance(cls, appearance):
        appearance = dict(cls.DEFAULT_APPEARANCE, **(appearance or {}))
        for name in ('fill', 'border_color'):
            value = appearance.get(name)
            if not _valid_color(value):
                appearance[name] = cls.DEFAULT_APPEARANCE[name]
            else:
                color = QtGui.QColor(value)
                name_format = (QtGui.QColor.NameFormat.HexRgb
                               if color.alpha() == 255
                               else QtGui.QColor.NameFormat.HexArgb)
                appearance[name] = color.name(name_format)
        appearance['border_width'] = max(
            0, float(appearance.get('border_width', 0)))
        appearance['radius'] = max(0, float(appearance.get('radius', 0)))
        return appearance

    def _apply_appearance(self, appearance):
        self.prepareGeometryChange()
        self.appearance = self._normalized_appearance(appearance)
        self.update()

    def _set_default_font_size(self, size):
        font = self.document().defaultFont()
        font.setPixelSize(int(size))
        self.document().setDefaultFont(font)

    def setTextWidth(self, width):
        self.prepareGeometryChange()
        self._text_width = float(width)
        super().setTextWidth(self._text_width)
        self.update()

    def text_state(self):
        return {
            'text': self.toPlainText(),
            'html': self.document().toHtml(),
            'font_size': self._font_size,
            'text_width': self._text_width,
            'appearance': copy.deepcopy(self.appearance),
        }

    def set_text_state(self, state):
        """Apply a complete rich-note state without adding history."""
        state = dict(state)
        self._applying_state = True
        self.prepareGeometryChange()
        try:
            self._font_size = state.get('font_size')
            if self._font_size is not None:
                self._font_size = int(self._font_size)
                self._set_default_font_size(self._font_size)
            self._apply_appearance(state.get('appearance'))
            self.setTextWidth(state.get('text_width', -1))
            if state.get('text', None) == '':
                # QTextDocument's HTML exporter represents an empty document
                # as a paragraph/newline.  Keep the plain fallback exactly
                # empty so placeholder/removal semantics remain stable.
                self.setPlainText('')
            elif state.get('html') is not None:
                self.document().setHtml(_sanitize_note_html(state['html']))
            else:
                self.setPlainText(state.get('text', ''))
        finally:
            self._applying_state = False
        self.update()

    def get_extra_save_data(self):
        return self.text_state()

    def contains(self, point):
        return self.boundingRect().contains(point)

    def paint(self, painter, option, widget):
        rect = QtWidgets.QGraphicsTextItem.boundingRect(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(QtGui.QColor(self.appearance['fill']))
        border_width = self.appearance['border_width']
        if border_width:
            painter.setPen(QtGui.QPen(
                QtGui.QColor(self.appearance['border_color']), border_width))
        else:
            painter.setPen(Qt.PenStyle.NoPen)
        inset = border_width / 2
        painter.drawRoundedRect(
            rect.adjusted(inset, inset, -inset, -inset),
            max(0, self.appearance['radius'] - inset),
            max(0, self.appearance['radius'] - inset))
        option.state = QtWidgets.QStyle.StateFlag.State_Enabled
        super().paint(painter, option, widget)
        self.paint_selectable(painter, option, widget)

    def create_copy(self):
        item = BeeTextItem(**self.text_state())
        item.setPos(self.pos())
        item.setZValue(self.zValue())
        item.setScale(self.scale())
        item.setRotation(self.rotation())
        if self.flip() == -1:
            item.do_flip()
        return item

    def _view(self):
        scene = self.scene()
        return scene.views()[0] if scene and scene.views() else None

    def _editing_changed(self, editing):
        view = self._view()
        callback = getattr(view, 'on_note_editing_changed', None)
        if callback:
            callback(self, editing)

    def _document_changed(self):
        self.prepareGeometryChange()
        self.update()
        if self.edit_mode and not self._applying_state:
            self._editing_changed(True)

    def enter_edit_mode(self, select_all=False):
        logger.debug(f'Entering edit mode on {self}')
        if self.edit_mode:
            return
        self.edit_mode = True
        self.old_text_state = self.text_state()
        # Old integrations inspected this field directly.
        self.old_text = self.old_text_state['text']
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextEditorInteraction)
        scene = self.scene()
        if scene:
            scene.edit_item = self
        cursor = self.textCursor()
        if select_all:
            cursor.select(QtGui.QTextCursor.SelectionType.Document)
        else:
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        self._editing_changed(True)

    def exit_edit_mode(self, commit=True):
        logger.debug(f'Exiting edit mode on {self}')
        if not self.edit_mode:
            return
        scene = self.scene()
        old_state = getattr(self, 'old_text_state', None)
        if old_state is None:
            # Compatibility for older callers that manually set edit_mode.
            old_state = self.text_state()
            old_state['text'] = getattr(self, 'old_text', old_state['text'])
            old_state.pop('html', None)
        new_state = self.text_state()
        self.edit_mode = False
        self.setTextCursor(QtGui.QTextCursor(self.document()))
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        if scene:
            scene.edit_item = None
        self._editing_changed(False)
        if not commit:
            self.set_text_state(old_state)
            return
        if scene and (new_state != old_state or not new_state['text'].strip()):
            scene.undo_stack.push(commands.ChangeText(
                self, new_state, old_state,
                remove_when_empty=not new_state['text'].strip()))

    def set_appearance(self, **kwargs):
        invalid = set(kwargs) - set(self.DEFAULT_APPEARANCE)
        if invalid:
            raise ValueError(
                f'Unknown note appearance fields: {sorted(invalid)}')
        before = self.text_state()
        after = copy.deepcopy(before)
        after['appearance'] = self._normalized_appearance(
            dict(after['appearance'], **kwargs))
        if self.edit_mode or self.scene() is None:
            # Do not replace the document while editing: it would lose the
            # active selection and QTextDocument's native undo history.
            self._apply_appearance(after['appearance'])
        elif after != before:
            self.scene().undo_stack.push(
                commands.ChangeText(self, after, before))

    def apply_format(self, kind, value=None):
        if kind == 'text_width':
            if value is None or not 120 <= float(value) <= 800:
                raise ValueError('text_width must be between 120 and 800')
            before = self.text_state()
            after = copy.deepcopy(before)
            after['text_width'] = float(value)
            if self.edit_mode or self.scene() is None:
                self.setTextWidth(after['text_width'])
            elif after != before:
                self.scene().undo_stack.push(
                    commands.ChangeText(self, after, before))
            return

        before = self.text_state()
        cursor = self.textCursor()
        if not self.edit_mode:
            cursor.select(QtGui.QTextCursor.SelectionType.Document)
        if kind == 'bold':
            if value is None:
                value = (cursor.charFormat().fontWeight()
                         < QtGui.QFont.Weight.Bold)
            value = bool(value)
            fmt = QtGui.QTextCharFormat()
            fmt.setFontWeight(QtGui.QFont.Weight.Bold if value
                              else QtGui.QFont.Weight.Normal)
        elif kind == 'italic':
            value = (not cursor.charFormat().fontItalic()
                     if value is None else bool(value))
            fmt = QtGui.QTextCharFormat()
            fmt.setFontItalic(value)
        elif kind == 'underline':
            value = (not cursor.charFormat().fontUnderline()
                     if value is None else bool(value))
            fmt = QtGui.QTextCharFormat()
            fmt.setFontUnderline(value)
        elif kind == 'strike':
            value = (not cursor.charFormat().fontStrikeOut()
                     if value is None else bool(value))
            fmt = QtGui.QTextCharFormat()
            fmt.setFontStrikeOut(value)
        elif kind == 'color':
            if not _valid_color(value):
                raise ValueError('color must be a valid QColor value')
            fmt = QtGui.QTextCharFormat()
            fmt.setForeground(QtGui.QColor(value))
        elif kind == 'font_size':
            if value is None or float(value) <= 0:
                raise ValueError('font_size must be positive')
            size = int(float(value))
            fmt = QtGui.QTextCharFormat()
            fmt.setProperty(QtGui.QTextFormat.Property.FontPixelSize, size)
        else:
            raise ValueError(f'Unknown note format: {kind}')

        cursor.mergeCharFormat(fmt)
        self.setTextCursor(cursor)
        if kind == 'font_size':
            self._font_size = size
            self._set_default_font_size(size)
        self.update()
        if not self.edit_mode and self.scene() is not None:
            after = self.text_state()
            if after != before:
                self.scene().undo_stack.push(
                    commands.ChangeText(self, after, before))

    def format_state(self):
        fmt = self.textCursor().charFormat()
        foreground = (fmt.foreground().color()
                      if fmt.foreground().style() != Qt.BrushStyle.NoBrush
                      else self.defaultTextColor())
        size = fmt.font().pixelSize()
        return {
            'bold': fmt.fontWeight() >= QtGui.QFont.Weight.Bold,
            'italic': fmt.fontItalic(),
            'underline': fmt.fontUnderline(),
            'strike': fmt.fontStrikeOut(),
            'color': foreground.name() if foreground.isValid() else None,
            # Legacy text items have a point-sized Qt default rather than a
            # logical pixel size.  The toolbar still needs a usable value.
            'font_size': size if size > 0 else (self._font_size or 18),
        }

    def paste_mime(self, mime, mode='auto'):
        if mode not in ('auto', 'plain', 'markdown'):
            raise ValueError('mode must be auto, plain, or markdown')
        if isinstance(mime, QtCore.QMimeData):
            html = mime.html() if mime.hasHtml() else None
            text = mime.text() if mime.hasText() else ''
            markdown = (
                bytes(mime.data('text/markdown')).decode('utf-8', 'replace')
                if mime.hasFormat('text/markdown') else None)
        elif isinstance(mime, dict):
            html, text = mime.get('html'), mime.get('text', '')
            markdown = mime.get('markdown')
        else:
            html, text, markdown = None, str(mime), None
        if mode == 'plain':
            self.textCursor().insertText(text)
        elif (mode == 'markdown' or (mode == 'auto' and markdown is not None)
              or (mode == 'auto' and not html and _looks_like_markdown(text))):
            document = QtGui.QTextDocument()
            features = (
                QtGui.QTextDocument.MarkdownFeature.MarkdownDialectGitHub)
            no_html = getattr(QtGui.QTextDocument.MarkdownFeature,
                              'MarkdownNoHTML', None)
            if no_html is not None:
                features |= no_html
            document.setMarkdown(markdown if markdown is not None else text,
                                 features)
            self.textCursor().insertHtml(
                _sanitize_note_html(document.toHtml()))
        elif html:
            self.textCursor().insertHtml(_sanitize_note_html(html))
        else:
            self.textCursor().insertText(text)

    def has_selection_handles(self):
        return super().has_selection_handles() and not self.edit_mode

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        if (event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return)
                and modifiers & (Qt.KeyboardModifier.ControlModifier
                                 | Qt.KeyboardModifier.MetaModifier)):
            self.exit_edit_mode()
            view = self._view()
            create_below = getattr(view, 'create_note_below', None)
            if create_below:
                create_below(self)
            event.accept()
            return
        # Enter is a normal rich-text newline. Escape is a convenient commit,
        # not a cancellation, so an editing session maps to board undo once.
        if (event.key() == Qt.Key.Key_Escape
                and modifiers == Qt.KeyboardModifier.NoModifier):
            self.exit_edit_mode()
            event.accept()
            return
        super().keyPressEvent(event)

    def copy_to_clipboard(self, clipboard):
        mime = QtCore.QMimeData()
        mime.setText(self.toPlainText())
        mime.setHtml(self.document().toHtml())
        clipboard.setMimeData(mime)


@register_item
class BeePathItem(BeeItemMixin, QtWidgets.QGraphicsItem):
    """A vector drawing made from pen strokes and geometric figures.

    ``base_size`` is retained in the serialized format for compatibility
    with the original drawing pull request. New figures also store ``tool``
    and ``style`` so old files continue to load as freehand solid strokes.
    """

    TYPE = 'path'

    def __init__(self, strokes=None, **kwargs):
        super().__init__()
        self.save_id = None
        self.is_image = False
        self.strokes = copy.deepcopy(strokes or [])
        self.temp_stroke = None
        self.erase_preview_indexes = set()
        self._cached_rect = QtCore.QRectF(0, 0, 1, 1)
        self.init_selectable()
        logger.debug(f'Initialized {self}')

    @classmethod
    def create_from_data(cls, **kwargs):
        data = kwargs.get('data', {})
        item = cls(strokes=data.get('strokes', []))
        item._update_bounding_rect()
        return item

    def __str__(self):
        n = len(self.strokes)
        return f'Drawing ({n} mark{"s" if n != 1 else ""})'

    def get_extra_save_data(self):
        return {'strokes': self.strokes}

    def create_copy(self):
        item = BeePathItem(strokes=copy.deepcopy(self.strokes))
        item.setPos(self.pos())
        item.setZValue(self.zValue())
        item.setScale(self.scale())
        item.setRotation(self.rotation())
        if self.flip() == -1:
            item.do_flip()
        item._update_bounding_rect()
        return item

    def contains(self, point):
        return self.shape().contains(point)

    def bounding_rect_unselected(self):
        rect = QtCore.QRectF(self._cached_rect)
        if self.temp_stroke:
            rect = rect.united(self._stroke_bounds(self.temp_stroke))
        return rect

    def add_stroke(self, stroke):
        self.prepareGeometryChange()
        self.strokes.append(copy.deepcopy(stroke))
        self._update_bounding_rect()
        self.update()

    def replace_strokes(self, strokes):
        """Replace all marks while keeping geometry notifications correct."""

        self.prepareGeometryChange()
        self.strokes = copy.deepcopy(strokes)
        self._update_bounding_rect()
        self.update()

    @staticmethod
    def _point(data):
        return QtCore.QPointF(data['x'], data['y'])

    @staticmethod
    def _effective_width(stroke):
        return float(stroke.get('base_size', stroke.get('width', 8)))

    def _stroke_path(self, stroke):
        points = stroke.get('points', [])
        path = QtGui.QPainterPath()
        if not points:
            return path

        start = self._point(points[0])
        end = self._point(points[-1])
        tool = stroke.get('tool', 'pen')

        if tool == 'rectangle':
            path.addRect(QtCore.QRectF(start, end).normalized())
        elif tool == 'ellipse':
            path.addEllipse(QtCore.QRectF(start, end).normalized())
        elif tool == 'line':
            path.moveTo(start)
            path.lineTo(end)
        else:
            path.moveTo(start)
            if len(points) == 1:
                path.lineTo(start + QtCore.QPointF(0.01, 0.01))
            elif len(points) == 2:
                path.lineTo(end)
            else:
                # Suppress high-frequency pointer jitter before interpolating.
                # Endpoints remain exact while the weighted interior samples
                # produce a calmer, ink-like curve at every zoom level.
                raw = [self._point(point) for point in points]
                vectors = [raw[0]]
                for index in range(1, len(raw) - 1):
                    vectors.append(
                        (raw[index - 1] + raw[index] * 2
                         + raw[index + 1]) / 4)
                vectors.append(raw[-1])
                for index in range(len(vectors) - 1):
                    before = vectors[max(0, index - 1)]
                    current = vectors[index]
                    following = vectors[index + 1]
                    after = vectors[min(len(vectors) - 1, index + 2)]
                    control_1 = current + (following - before) / 6
                    control_2 = following - (after - current) / 6
                    path.cubicTo(control_1, control_2, following)
        return path

    def _arrow_path(self, stroke):
        if (stroke.get('style') != 'arrow'
                or stroke.get('tool', 'pen') not in ('pen', 'line')):
            return QtGui.QPainterPath()
        points = stroke.get('points', [])
        if len(points) < 2:
            return QtGui.QPainterPath()
        end = self._point(points[-1])
        previous = self._point(points[-2])
        if stroke.get('tool', 'pen') == 'line':
            previous = self._point(points[0])
        angle = math.atan2(end.y() - previous.y(), end.x() - previous.x())
        length = max(10.0, self._effective_width(stroke) * 3.0)
        spread = math.radians(28)
        p1 = end - QtCore.QPointF(
            math.cos(angle - spread) * length,
            math.sin(angle - spread) * length)
        p2 = end - QtCore.QPointF(
            math.cos(angle + spread) * length,
            math.sin(angle + spread) * length)
        path = QtGui.QPainterPath(end)
        path.lineTo(p1)
        path.moveTo(end)
        path.lineTo(p2)
        return path

    def _stroke_bounds(self, stroke):
        path = self._stroke_path(stroke)
        path.addPath(self._arrow_path(stroke))
        width = self._effective_width(stroke)
        margin = width / 2 + 3
        return path.boundingRect().marginsAdded(
            QtCore.QMarginsF(margin, margin, margin, margin))

    def _update_bounding_rect(self):
        if not self.strokes:
            self._cached_rect = QtCore.QRectF(0, 0, 1, 1)
            return
        rect = QtCore.QRectF()
        for stroke in self.strokes:
            bounds = self._stroke_bounds(stroke)
            rect = bounds if rect.isNull() else rect.united(bounds)
        self._cached_rect = (
            rect if not rect.isNull() else QtCore.QRectF(0, 0, 1, 1))

    def _paint_stroke(self, painter, stroke):
        color_data = stroke.get('color', [235, 235, 238, 255])
        color = QtGui.QColor(*color_data)
        base_size = self._effective_width(stroke)
        points = stroke.get('points', [])
        if not points:
            return

        pen = QtGui.QPen(color, base_size)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        if stroke.get('style') == 'dotted':
            pen.setStyle(Qt.PenStyle.DotLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        tool = stroke.get('tool', 'pen')
        if tool == 'pen' and any('pressure' in point for point in points):
            pressure = sum(
                point.get('pressure', 1.0) for point in points) / len(points)
            pen.setWidthF(max(0.5, base_size * pressure))
            painter.setPen(pen)
        painter.drawPath(self._stroke_path(stroke))

        arrow = self._arrow_path(stroke)
        if not arrow.isEmpty():
            pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawPath(arrow)

    def stroke_indexes_at(self, point, radius):
        """Return marks intersecting an eraser centered on ``point``."""

        eraser = QtGui.QPainterPath()
        eraser.addEllipse(point, radius, radius)
        matches = []
        for index, stroke in enumerate(self.strokes):
            path = self._stroke_path(stroke)
            path.addPath(self._arrow_path(stroke))
            stroker = QtGui.QPainterPathStroker()
            stroker.setWidth(self._effective_width(stroke) + radius * 2)
            if stroker.createStroke(path).intersects(eraser):
                matches.append(index)
        return matches

    def erase_at(self, point, radius):
        indexes = self.stroke_indexes_at(point, radius)
        return self.erase_indexes(indexes)

    def set_erase_preview(self, indexes):
        """Fade marks that will be removed when the erase drag ends."""

        self.erase_preview_indexes = set(indexes)
        self.update()

    def erase_indexes(self, indexes):
        indexes = sorted(set(indexes), reverse=True)
        if not indexes:
            return False
        self.prepareGeometryChange()
        for index in indexes:
            if 0 <= index < len(self.strokes):
                self.strokes.pop(index)
        self.erase_preview_indexes.clear()
        self._update_bounding_rect()
        self.update()
        return True

    def shape(self):
        if self.has_selection_handles():
            return super().shape()
        result = QtGui.QPainterPath()
        for stroke in self.strokes:
            stroker = QtGui.QPainterPathStroker()
            stroker.setWidth(max(8, self._effective_width(stroke) + 4))
            result.addPath(stroker.createStroke(self._stroke_path(stroke)))
            result.addPath(stroker.createStroke(self._arrow_path(stroke)))
        return result

    def paint(self, painter, option, widget):
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        for index, stroke in enumerate(self.strokes):
            painter.save()
            if index in self.erase_preview_indexes:
                painter.setOpacity(0.16)
            self._paint_stroke(painter, stroke)
            painter.restore()
        if self.temp_stroke:
            self._paint_stroke(painter, self.temp_stroke)

        self.paint_selectable(painter, option, widget)

    def render_to_image(self):
        rect = self.bounding_rect_unselected()
        image = QtGui.QImage(
            max(1, math.ceil(rect.width())),
            max(1, math.ceil(rect.height())),
            QtGui.QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(image)
        painter.translate(-rect.topLeft())
        for stroke in self.strokes:
            self._paint_stroke(painter, stroke)
        painter.end()
        return image, rect

    def copy_to_clipboard(self, clipboard):
        image, _ = self.render_to_image()
        clipboard.setImage(image)


@register_item
class BeeErrorItem(BeeItemMixin, QtWidgets.QGraphicsTextItem):
    """Class for displaying error messages when an item can't be loaded
    from a bee file.

    This item will be displayed instead of the original item. It won't
    save to bee files. The original item will be preserved in the bee
    file, unless this item gets deleted by the user, or a new bee file
    is saved.
    """

    TYPE = 'error'

    def __init__(self, text=None, **kwargs):
        super().__init__(text or "Text")
        self.original_save_id = None
        logger.debug(f'Initialized {self}')
        self.is_image = False
        self.init_selectable()
        self.is_editable = False
        self.setDefaultTextColor(QtGui.QColor(*COLORS['Scene:Text']))

    @classmethod
    def create_from_data(cls, **kwargs):
        data = kwargs.get('data', {})
        item = cls(**data)
        return item

    def __str__(self):
        txt = self.toPlainText()[:40]
        return (f'Error "{txt}"')

    def contains(self, point):
        return self.boundingRect().contains(point)

    def paint(self, painter, option, widget):
        painter.setPen(Qt.PenStyle.NoPen)
        color = QtGui.QColor(200, 0, 0)
        brush = QtGui.QBrush(color)
        painter.setBrush(brush)
        painter.drawRect(QtWidgets.QGraphicsTextItem.boundingRect(self))
        option.state = QtWidgets.QStyle.StateFlag.State_Enabled
        super().paint(painter, option, widget)
        self.paint_selectable(painter, option, widget)

    def update_from_data(self, **kwargs):
        self.original_save_id = kwargs.get('save_id', self.original_save_id)
        self.setPos(kwargs.get('x', self.pos().x()),
                    kwargs.get('y', self.pos().y()))
        self.setZValue(kwargs.get('z', self.zValue()))
        self.setScale(kwargs.get('scale', self.scale()))
        self.setRotation(kwargs.get('rotation', self.rotation()))

    def create_copy(self):
        item = BeeErrorItem(self.toPlainText())
        item.setPos(self.pos())
        item.setZValue(self.zValue())
        item.setScale(self.scale())
        item.setRotation(self.rotation())
        return item

    def flip(self, *args, **kwargs):
        """Returns the flip value (1 or -1)"""
        # Never display error messages flipped
        return 1

    def do_flip(self, *args, **kwargs):
        """Flips the item."""
        # Never flip error messages
        pass

    def copy_to_clipboard(self, clipboard):
        clipboard.setText(self.toPlainText())
