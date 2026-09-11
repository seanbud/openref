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

from functools import partial
import copy
import logging
import math
import os
import os.path
import sys

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt

from beeref.actions import ActionsMixin, actions
from beeref import commands
from beeref.config import (
    CommandlineArgs,
    BeeSettings,
    KeyboardSettings,
    settings_events,
)
from beeref import constants
from beeref import fileio
from beeref.fileio.errors import IMG_LOADING_ERROR_MSG
from beeref.fileio.export import exporter_registry, ImagesToDirectoryExporter
from beeref import widgets
from beeref.items import BeePixmapItem, BeeTextItem, BeePathItem
from beeref.main_controls import MainControlsMixin
from beeref.scene import BeeGraphicsScene
from beeref.utils import get_file_extension_from_format, qcolor_to_hex


commandline_args = CommandlineArgs()
logger = logging.getLogger(__name__)


class BeeGraphicsView(MainControlsMixin,
                      QtWidgets.QGraphicsView,
                      ActionsMixin):

    PAN_MODE = 1
    ZOOM_MODE = 2
    SAMPLE_COLOR_MODE = 3
    DRAW_MODE = 4

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.parent = parent
        self.settings = BeeSettings()
        self.keyboard_settings = KeyboardSettings()
        self.welcome_overlay = widgets.welcome_overlay.WelcomeOverlay(self)

        self.setBackgroundBrush(
            QtGui.QBrush(QtGui.QColor(*constants.COLORS['Scene:Canvas'])))
        self.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)

        self.undo_stack = QtGui.QUndoStack(self)
        self.undo_stack.setUndoLimit(100)
        self.undo_stack.canRedoChanged.connect(self.on_can_redo_changed)
        self.undo_stack.canUndoChanged.connect(self.on_can_undo_changed)
        self.undo_stack.cleanChanged.connect(self.on_undo_clean_changed)

        self.filename = None
        self.previous_transform = None
        self.active_mode = None
        self._hud_toast = None
        self._ready_for_feedback = False
        self._syncing_actions = False
        self.draw_item = None
        self.draw_current_stroke = None
        self.draw_brush_size = 8.0
        self.draw_brush_color = [235, 235, 238, 255]
        self.draw_tool = 'pen'
        self.draw_style = 'solid'
        self._draw_editing_existing = False
        self._draw_original_strokes = None
        self._draw_panning = False
        self._tablet_pressure = 1.0
        self._temporary_eraser_tool = None
        self._eraser_candidates = {}
        self._eraser_active = False
        self._right_canvas_panning = False
        self._right_canvas_pending = False
        self._fullscreen_anchor = None
        self._fullscreen_anchor_timer = QtCore.QTimer(self)
        self._fullscreen_anchor_timer.setSingleShot(True)
        self._fullscreen_anchor_timer.timeout.connect(
            self._clear_fullscreen_anchor)
        self.window_position_locked = False
        self._recalculating_scene_rect = False

        self.scene = BeeGraphicsScene(self.undo_stack)
        self.scene.changed.connect(self.on_scene_changed)
        self.scene.selectionChanged.connect(self.on_selection_changed)
        self.scene.cursor_changed.connect(self.on_cursor_changed)
        self.scene.cursor_cleared.connect(self.on_cursor_cleared)
        self.setScene(self.scene)

        # Context menu and actions
        self.build_menu_and_actions()
        self.control_target = self
        self.init_main_controls(main_window=parent)
        self.draw_toolbar = widgets.drawing_toolbar.DrawingToolbar(
            self.viewport())
        self.draw_toolbar.tool_changed.connect(self.set_draw_tool)
        self.draw_toolbar.style_changed.connect(self.set_draw_style)
        self.draw_toolbar.width_changed.connect(self.set_draw_width)
        self.draw_toolbar.color_requested.connect(
            self.on_action_set_brush_color)
        self.draw_toolbar.close_requested.connect(
            lambda: self.exit_draw_mode(commit=True))
        self.draw_toolbar.hide()
        self.eraser_trail = widgets.modern_ui.EraserTrailOverlay(
            self.viewport())
        self.eraser_trail.stackUnder(self.draw_toolbar)
        pin_action = actions.actions['always_on_top'].qaction
        self.window_chrome = widgets.modern_ui.WindowChrome(
            self, parent,
            lambda checked: pin_action.setChecked(checked),
            close_callback=self.on_action_quit,
            hover_targets=(self.viewport(), self.welcome_overlay))
        self.window_chrome.set_pinned(pin_action.isChecked())
        self.window_chrome.set_enabled(bool(
            parent.windowFlags() & Qt.WindowType.FramelessWindowHint))
        settings_events.appearance_changed.connect(
            self.on_appearance_changed)

        # Load files given via command line
        if commandline_args.filenames:
            fn = commandline_args.filenames[0]
            if os.path.splitext(fn)[1] == '.bee':
                self.open_from_file(fn)
            else:
                self.do_insert_images(commandline_args.filenames)

        self.update_window_title()
        self._ready_for_feedback = True

    def show_feedback(self, text, icon='✓', action_id=None,
                      shortcut=None, duration=None):
        """Show transient canvas feedback for a completed user action."""

        if not self._ready_for_feedback:
            return
        if shortcut is None and action_id:
            definition = actions.actions.get(action_id)
            if definition and definition.qaction:
                shortcut = definition.qaction.shortcut().toString(
                    QtGui.QKeySequence.SequenceFormat.NativeText)
        if self._hud_toast is None:
            self._hud_toast = widgets.BeeNotification(
                self, text, icon=icon, shortcut=shortcut,
                duration=duration)
        else:
            self._hud_toast.present(
                text, icon=icon, shortcut=shortcut, duration=duration)

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, value):
        self._filename = value
        self.update_window_title()
        if value:
            self.settings.update_recent_files(value)
            self.update_menu_and_actions()

    def cancel_active_modes(self):
        self.scene.cancel_active_modes()
        if self.active_mode == self.DRAW_MODE:
            self.exit_draw_mode(commit=True)
        elif self.active_mode == self.SAMPLE_COLOR_MODE:
            self.cancel_sample_color_mode()
        else:
            self.active_mode = None

    def cancel_sample_color_mode(self):
        logger.debug('Cancel sample color mode')
        self.active_mode = None
        self.viewport().unsetCursor()
        if hasattr(self, 'sample_color_widget'):
            self.sample_color_widget.hide()
            del self.sample_color_widget
        if self.scene.has_multi_selection():
            self.scene.multi_select_item.bring_to_front()

    def update_window_title(self):
        clean = self.undo_stack.isClean()
        if clean and not self.filename:
            title = constants.APPNAME
        else:
            name = os.path.basename(self.filename or '[Untitled]')
            clean = '' if clean else '*'
            title = f'{name}{clean} - {constants.APPNAME}'
        self.parent.setWindowTitle(title)

    def on_scene_changed(self, region):
        if not self.scene.items():
            logger.debug('No items in scene')
            self.setTransform(QtGui.QTransform())
            self.welcome_overlay.setFocus()
            self.clearFocus()
            self.welcome_overlay.show()
            self.actiongroup_set_enabled('active_when_items_in_scene', False)
        else:
            self.setFocus()
            self.welcome_overlay.clearFocus()
            self.welcome_overlay.hide()
            self.actiongroup_set_enabled('active_when_items_in_scene', True)
            self.scene.expand_used_space()
        self.recalc_scene_rect()

    def on_can_redo_changed(self, can_redo):
        self.actiongroup_set_enabled('active_when_can_redo', can_redo)

    def on_can_undo_changed(self, can_undo):
        self.actiongroup_set_enabled('active_when_can_undo', can_undo)

    def on_undo_clean_changed(self, clean):
        self.update_window_title()

    def on_context_menu(self, point):
        self.context_menu.exec(self.mapToGlobal(point))

    def get_supported_image_formats(self, cls):
        formats = []

        for f in cls.supportedImageFormats():
            string = f'*.{f.data().decode()}'
            formats.extend((string, string.upper()))
        return ' '.join(formats)

    def get_view_center(self):
        return QtCore.QPoint(round(self.size().width() / 2),
                             round(self.size().height() / 2))

    def clear_scene(self):
        logging.debug('Clearing scene...')
        self.cancel_active_modes()
        self.scene.clear()
        self.undo_stack.clear()
        self.filename = None
        self.setTransform(QtGui.QTransform())

    def reset_previous_transform(self, toggle_item=None):
        if (self.previous_transform
                and self.previous_transform['toggle_item'] != toggle_item):
            self.previous_transform = None

    def fit_rect(self, rect, toggle_item=None):
        if toggle_item and self.previous_transform:
            logger.debug('Fit view: Reset to previous')
            self.setTransform(self.previous_transform['transform'])
            self.centerOn(self.previous_transform['center'])
            self.previous_transform = None
            return
        if toggle_item:
            self.previous_transform = {
                'toggle_item': toggle_item,
                'transform': QtGui.QTransform(self.transform()),
                'center': self.mapToScene(self.get_view_center()),
            }
        else:
            self.previous_transform = None

        logger.debug(f'Fit view: {rect}')
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
        self.recalc_scene_rect()
        # It seems to be more reliable when we fit a second time
        # Sometimes a changing scene rect can mess up the fitting
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
        logger.trace('Fit view done')

    def get_confirmation_unsaved_changes(self, msg):
        confirm = self.settings.valueOrDefault('Save/confirm_close_unsaved')
        if confirm and not self.undo_stack.isClean():
            choice, remember = (
                widgets.modern_ui.UnsavedChangesDialog.get_choice(self, msg))
            if choice == widgets.modern_ui.UnsavedChangesDialog.SAVE:
                self.on_action_save()
                self.show_feedback(
                    'Saving—repeat the action when complete', '✓',
                    duration=2200)
                return False
            if choice == widgets.modern_ui.UnsavedChangesDialog.DISCARD:
                if remember:
                    self.settings.setValue(
                        'Save/confirm_close_unsaved', False)
                return True
            return False

        return True

    def on_action_new_scene(self):
        confirm = self.get_confirmation_unsaved_changes(
            'There are unsaved changes. '
            'Are you sure you want to open a new scene?')
        if confirm:
            self.clear_scene()

    def on_action_fit_scene(self):
        if self.active_mode == self.DRAW_MODE:
            self.set_draw_style('solid')
            return
        old_rect = QtCore.QRectF(self.scene.used_space_rect)
        rect = self.scene.optimized_used_space_rect()
        if rect != old_rect:
            self.undo_stack.push(commands.ChangeCanvasBounds(
                self.scene, rect, old_rect))
        if not rect.isNull() and not rect.isEmpty():
            self.fit_rect(rect)
        self.viewport().update()
        self.show_feedback('Canvas fitted', '⌗', 'fit_scene')

    def on_action_fit_selection(self):
        self.fit_rect(self.scene.itemsBoundingRect(selection_only=True))
        self.show_feedback('Selection framed', '⌗', 'fit_selection')

    def on_action_fullscreen(self, checked):
        anchor_view = self.viewport().rect().center()
        anchor_scene = self.mapToScene(anchor_view)
        anchor_global = self.viewport().mapToGlobal(anchor_view)
        self._fullscreen_anchor = (anchor_scene, anchor_global)
        self._fullscreen_anchor_timer.start(450)
        if checked:
            self.parent.showFullScreen()
        else:
            self.parent.showNormal()
        QtCore.QTimer.singleShot(
            0, lambda: self._restore_global_canvas_anchor(
                anchor_scene, anchor_global))
        self.show_feedback(
            'Fullscreen enabled' if checked else 'Fullscreen disabled',
            '⛶', 'fullscreen')

    def _restore_global_canvas_anchor(self, scene_point, global_point):
        """Keep canvas content pinned to its pre-transition screen point."""

        local_anchor = self.viewport().mapFromGlobal(global_point)
        self.pan(self.mapFromScene(scene_point) - local_anchor)
        self.reset_previous_transform()

    def _clear_fullscreen_anchor(self):
        self._fullscreen_anchor = None

    def on_action_always_on_top(self, checked):
        self.parent.setWindowFlag(
            Qt.WindowType.WindowStaysOnTopHint, on=checked)
        self.parent.destroy()
        self.parent.create()
        self.parent.show()
        if hasattr(self, 'window_chrome'):
            self.window_chrome.set_pinned(checked)
        self.show_feedback(
            'Always on top enabled' if checked
            else 'Always on top disabled',
            '◧', 'always_on_top')

    def on_action_show_scrollbars(self, checked):
        if checked:
            self.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            self.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.show_feedback(
            'Scrollbars shown' if checked else 'Scrollbars hidden',
            '☷', 'show_scrollbars')

    def on_action_show_menubar(self, checked):
        if checked:
            self.parent.setMenuBar(self.create_menubar())
        else:
            self.parent.setMenuBar(None)
        self.show_feedback(
            'Menu bar shown' if checked else 'Menu bar hidden',
            '≡', 'show_menubar')

    def on_action_show_titlebar(self, checked):
        self.parent.setWindowFlag(
            Qt.WindowType.FramelessWindowHint, on=not checked)
        self.parent.destroy()
        self.parent.create()
        self.parent.show()
        if hasattr(self, 'window_chrome'):
            self.window_chrome.set_enabled(not checked)
        self.show_feedback(
            'Title bar shown' if checked else 'Title bar hidden',
            '▭', 'show_titlebar')

    def on_action_move_window(self):
        if self.welcome_overlay.isHidden():
            self.on_action_movewin_mode()
        else:
            self.welcome_overlay.on_action_movewin_mode()
        self.show_feedback('Move window · drag anywhere', '✥',
                           'move_window', duration=2000)

    def on_action_lock_window(self, checked):
        self.window_position_locked = checked
        self.show_feedback(
            'Window position locked' if checked
            else 'Window position unlocked',
            '◆' if checked else '◇', 'lock_window')

    def on_action_undo(self):
        logger.debug('Undo: %s' % self.undo_stack.undoText())
        self.cancel_active_modes()
        label = self.undo_stack.undoText()
        self.undo_stack.undo()
        if label:
            self.show_feedback(f'Undid {label.lower()}', '↶', 'undo')

    def on_action_redo(self):
        logger.debug('Redo: %s' % self.undo_stack.redoText())
        self.cancel_active_modes()
        label = self.undo_stack.redoText()
        self.undo_stack.redo()
        if label:
            self.show_feedback(f'Redid {label.lower()}', '↷', 'redo')

    def on_action_select_all(self):
        self.scene.select_all_items()
        count = len(self.scene.selectedItems(user_only=True))
        self.show_feedback(f'Selected {count} item{"s" if count != 1 else ""}',
                           '▣', 'select_all')

    def on_action_deselect_all(self):
        self.scene.deselect_all_items()
        self.show_feedback('Selection cleared', '□', 'deselect_all')

    def on_action_delete_items(self):
        logger.debug('Deleting items...')
        self.cancel_active_modes()
        selected = self.scene.selectedItems(user_only=True)
        self.undo_stack.push(
            commands.DeleteItems(
                self.scene, selected))
        count = len(selected)
        self.show_feedback(f'Deleted {count} item{"s" if count != 1 else ""}',
                           '⌫', 'delete')

    def on_action_cut(self):
        logger.debug('Cutting items...')
        self.on_action_copy()
        self.undo_stack.push(
            commands.DeleteItems(
                self.scene, self.scene.selectedItems(user_only=True)))

    def on_action_raise_to_top(self):
        self.scene.raise_to_top()
        self.show_feedback('Brought selection to front', '↑',
                           'raise_to_top')

    def on_action_lower_to_bottom(self):
        self.scene.lower_to_bottom()
        self.show_feedback('Sent selection to back', '↓',
                           'lower_to_bottom')

    def on_action_normalize_height(self):
        self.scene.normalize_height()
        self.show_feedback('Matched heights', '↕', 'normalize_height')

    def on_action_normalize_width(self):
        self.scene.normalize_width()
        self.show_feedback('Matched widths', '↔', 'normalize_width')

    def on_action_normalize_size(self):
        self.scene.normalize_size()
        self.show_feedback('Matched sizes', '⤢', 'normalize_size')

    def on_action_arrange_horizontal(self):
        self.scene.arrange()
        self.show_feedback('Arranged horizontally', '↔',
                           'arrange_horizontal')

    def on_action_arrange_vertical(self):
        self.scene.arrange(vertical=True)
        self.show_feedback('Arranged vertically', '↕',
                           'arrange_vertical')

    def on_action_arrange_optimal(self):
        self.scene.arrange_optimal()
        self.show_feedback('Optimally arranged', '▦', 'arrange_optimal')

    def on_action_arrange_square(self):
        self.scene.arrange_square()
        self.show_feedback('Arranged in a grid', '▦', 'arrange_square')

    def on_action_change_opacity(self):
        images = list(filter(
            lambda item: item.is_image,
            self.scene.selectedItems(user_only=True)))
        widgets.ChangeOpacityDialog(self, images, self.undo_stack)

    def on_action_grayscale(self, checked):
        if self._syncing_actions:
            return
        images = list(filter(
            lambda item: item.is_image,
            self.scene.selectedItems(user_only=True)))
        if images:
            self.undo_stack.push(
                commands.ToggleGrayscale(images, checked))
            self.show_feedback(
                'Grayscale enabled' if checked else 'Grayscale disabled',
                '◐', 'grayscale')

    def on_action_crop(self):
        self.scene.crop_items()
        self.show_feedback('Crop mode · Enter applies · Esc cancels',
                           '⌗', 'crop', duration=2200)

    def on_action_flip_horizontally(self):
        self.scene.flip_items(vertical=False)
        self.show_feedback('Flipped horizontally', '↔',
                           'flip_horizontally')

    def on_action_flip_vertically(self):
        self.scene.flip_items(vertical=True)
        self.show_feedback('Flipped vertically', '↕',
                           'flip_vertically')

    def on_action_reset_scale(self):
        self.cancel_active_modes()
        self.undo_stack.push(commands.ResetScale(
            self.scene.selectedItems(user_only=True)))
        self.show_feedback('Scale reset', '⤢', 'reset_scale')

    def on_action_reset_rotation(self):
        self.cancel_active_modes()
        self.undo_stack.push(commands.ResetRotation(
            self.scene.selectedItems(user_only=True)))
        self.show_feedback('Rotation reset', '↺', 'reset_rotation')

    def on_action_reset_flip(self):
        self.cancel_active_modes()
        self.undo_stack.push(commands.ResetFlip(
            self.scene.selectedItems(user_only=True)))
        self.show_feedback('Flip reset', '⇄', 'reset_flip')

    def on_action_reset_crop(self):
        self.cancel_active_modes()
        self.undo_stack.push(commands.ResetCrop(
            self.scene.selectedItems(user_only=True)))
        self.show_feedback('Crop reset', '⌗', 'reset_crop')

    def on_action_reset_transforms(self):
        self.cancel_active_modes()
        self.undo_stack.push(commands.ResetTransforms(
            self.scene.selectedItems(user_only=True)))
        self.show_feedback('Transforms reset', '↺', 'reset_transforms')

    def on_action_show_color_gamut(self):
        widgets.color_gamut.GamutDialog(self, self.scene.selectedItems()[0])

    def on_action_sample_color(self):
        self.cancel_active_modes()
        logger.debug('Entering sample color mode')
        self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        self.active_mode = self.SAMPLE_COLOR_MODE

        if self.scene.has_multi_selection():
            # We don't want to sample the multi select item, so
            # temporarily send it to the back:
            self.scene.multi_select_item.lower_behind_selection()

        pos = self.mapFromGlobal(self.cursor().pos())
        self.sample_color_widget = widgets.SampleColorWidget(
            self,
            pos,
            self.scene.sample_color_at(self.mapToScene(pos)))
        self.show_feedback('Color picker · click to copy', '◉',
                           'sample_color', duration=2000)

    def on_action_draw_mode(self):
        if self.active_mode == self.DRAW_MODE:
            self.exit_draw_mode(commit=True)
        else:
            self.enter_draw_mode()

    def enter_draw_mode(self, item=None):
        """Enter drawing mode, optionally editing an existing drawing."""

        self.cancel_active_modes()
        self.scene.deselect_all_items()
        self.draw_item = item
        self._draw_editing_existing = item is not None
        self._draw_original_strokes = (
            copy.deepcopy(item.strokes) if item is not None else None)
        self.active_mode = self.DRAW_MODE
        self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        self.setFocus()
        self.welcome_overlay.hide()
        self.draw_toolbar.set_tool(self.draw_tool)
        self.draw_toolbar.set_style(self.draw_style)
        self.draw_toolbar.set_width(self.draw_brush_size)
        self.draw_toolbar.set_color(QtGui.QColor(*self.draw_brush_color))
        self._position_draw_toolbar()
        self.draw_toolbar.show()
        self.draw_toolbar.raise_()
        logger.debug('Entered draw mode')
        self.show_feedback('Draw mode enabled', '✎', 'draw_mode')

    def exit_draw_mode(self, commit=True):
        logger.debug(f'Exiting draw mode, commit={commit}')
        self._clear_eraser_preview()
        self._temporary_eraser_tool = None
        if self.draw_item:
            if self.draw_current_stroke:
                self.draw_item.add_stroke(self.draw_current_stroke)
                self.draw_item.temp_stroke = None
                self.draw_current_stroke = None
            if self._draw_editing_existing:
                before = self._draw_original_strokes or []
                after = copy.deepcopy(self.draw_item.strokes)
                if not commit:
                    self.draw_item.replace_strokes(before)
                elif before != after:
                    if not after:
                        # Preserve the original contents inside the delete
                        # command so undo restores a usable drawing item.
                        self.draw_item.replace_strokes(before)
                        self.undo_stack.push(commands.DeleteItems(
                            self.scene, [self.draw_item]))
                    else:
                        self.undo_stack.push(commands.ChangeDrawing(
                            self.draw_item, after, before,
                            ignore_first_redo=True))
            elif commit and self.draw_item.strokes:
                self.scene.removeItem(self.draw_item)
                self.undo_stack.push(
                    commands.InsertItems(
                        self.scene, [self.draw_item]))
            elif self.draw_item.scene():
                self.scene.removeItem(self.draw_item)
            self.draw_item = None
        self._draw_editing_existing = False
        self._draw_original_strokes = None
        self._draw_panning = False
        self.active_mode = None
        self.draw_toolbar.hide()
        self.viewport().unsetCursor()
        # Leaving draw mode is already visually obvious when the toolbar and
        # cursor disappear; a success toast here only obscures the canvas.

    def set_draw_tool(self, tool, announce=True):
        self.draw_tool = tool
        self.draw_toolbar.set_tool(tool)
        cursor = (Qt.CursorShape.CrossCursor
                  if tool != 'eraser'
                  else Qt.CursorShape.PointingHandCursor)
        self.viewport().setCursor(cursor)
        if self.active_mode == self.DRAW_MODE and announce:
            labels = {
                'pen': ('Pen', '✎', 'D'),
                'line': ('Line', '╱', 'L'),
                'rectangle': ('Rectangle', '□', 'R'),
                'ellipse': ('Ellipse', '○', 'C'),
                'eraser': ('Eraser', '⌫', 'E'),
            }
            label, icon, shortcut = labels[tool]
            self.show_feedback(label, icon, shortcut=shortcut)

    def set_draw_style(self, style):
        self.draw_style = style
        self.draw_toolbar.set_style(style)
        if self.active_mode == self.DRAW_MODE:
            labels = {
                'solid': ('Solid stroke', '━', '1'),
                'dotted': ('Dotted stroke', '┅', '2'),
                'arrow': ('Arrow stroke', '↗', '3'),
            }
            label, icon, shortcut = labels[style]
            self.show_feedback(label, icon, shortcut=shortcut)

    def set_draw_width(self, width):
        self.draw_brush_size = float(width)
        if self.active_mode == self.DRAW_MODE:
            self.show_feedback(f'{int(width)} px stroke', '●',
                               shortcut='[  ]', duration=900)

    def on_action_set_brush_color(self):
        current = QtGui.QColor(*self.draw_brush_color)
        dialog = widgets.modern_ui.ColorPickerDialog(current, self)
        dialog.color_changed.connect(self.draw_toolbar.set_color)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            color = dialog.selectedColor()
            self.draw_brush_color = [
                color.red(), color.green(), color.blue(), color.alpha()]
            self.draw_toolbar.set_color(color)
            self.show_feedback(
                f'Stroke color {color.name().upper()}', '●',
                shortcut='Ctrl+T')
        else:
            self.draw_toolbar.set_color(current)

    def on_action_set_brush_size(self):
        size, ok = QtWidgets.QInputDialog.getInt(
            self, 'Brush Size', 'Size (px):',
            int(self.draw_brush_size), 1, 500)
        if ok:
            self.draw_toolbar.set_width(size)

    def on_action_command_palette(self):
        self.command_palette = widgets.drawing_toolbar.CommandPalette(
            self, actions.actions.values())
        center = self.mapToGlobal(self.rect().center())
        self.command_palette.move(
            center.x() - self.command_palette.width() // 2,
            center.y() - self.command_palette.height() // 2)
        self.command_palette.open()

    def _position_draw_toolbar(self):
        hint = self.draw_toolbar.sizeHint()
        margin = 12
        position = self.settings.valueOrDefault(
            'Appearance/drawing_toolbar_position')
        on_right = position.endswith('right')
        on_bottom = position.startswith('bottom')
        x = (self.viewport().width() - hint.width() - margin
             if on_right else margin)
        y = (self.viewport().height() - hint.height() - margin
             if on_bottom else margin)
        x = max(margin, x)
        y = max(margin, y)
        self.draw_toolbar.move(x, y)

    def on_appearance_changed(self):
        from beeref.theme import apply_theme

        apply_theme(
            self.app, self.settings.valueOrDefault('Appearance/theme'))
        self._position_draw_toolbar()
        self.viewport().update()

    @staticmethod
    def _constrained_point(start, end, tool):
        delta = end - start
        if tool in ('rectangle', 'ellipse'):
            size = max(abs(delta.x()), abs(delta.y()))
            return start + QtCore.QPointF(
                math.copysign(size, delta.x() or 1),
                math.copysign(size, delta.y() or 1))
        angle = math.atan2(delta.y(), delta.x())
        distance = math.hypot(delta.x(), delta.y())
        snapped = round(angle / (math.pi / 4)) * (math.pi / 4)
        return start + QtCore.QPointF(
            math.cos(snapped) * distance,
            math.sin(snapped) * distance)

    def _new_drawing_at(self, scene_pos):
        self.draw_item = BeePathItem()
        self.draw_item.setPos(scene_pos)
        self.scene.addItem(self.draw_item)
        self.draw_item.bring_to_front()

    def _find_drawing_at(self, scene_pos, radius):
        area = QtCore.QRectF(
            scene_pos.x() - radius, scene_pos.y() - radius,
            radius * 2, radius * 2)
        for item in self.scene.items(area):
            if isinstance(item, BeePathItem):
                local = item.mapFromScene(scene_pos)
                if item.stroke_indexes_at(local, radius / item.scale()):
                    return item

    def _begin_eraser(self, scene_pos, view_pos=None):
        """Begin a non-destructive erase preview."""

        self._clear_eraser_preview()
        self._eraser_active = True
        view_pos = view_pos or self.mapFromScene(scene_pos)
        self.eraser_trail.begin(view_pos, self.draw_brush_size)
        self._preview_erase_at(scene_pos, view_pos)

    def _preview_erase_at(self, scene_pos, view_pos=None):
        if not self._eraser_active:
            return
        view_pos = view_pos or self.mapFromScene(scene_pos)
        self.eraser_trail.add_point(view_pos)
        scene_radius = self.draw_brush_size / max(self.get_scale(), 0.0001)
        area = QtCore.QRectF(
            scene_pos.x() - scene_radius,
            scene_pos.y() - scene_radius,
            scene_radius * 2, scene_radius * 2)
        for item in self.scene.items(area):
            if not isinstance(item, BeePathItem):
                continue
            local = item.mapFromScene(scene_pos)
            local_radius = scene_radius / max(abs(item.scale()), 0.0001)
            indexes = item.stroke_indexes_at(local, local_radius)
            if not indexes:
                continue
            candidates = self._eraser_candidates.setdefault(item, set())
            candidates.update(indexes)
            item.set_erase_preview(candidates)

    def _clear_eraser_preview(self):
        for item in self._eraser_candidates:
            item.set_erase_preview(())
        self._eraser_candidates = {}
        self._eraser_active = False
        if hasattr(self, 'eraser_trail'):
            self.eraser_trail.cancel()

    def _commit_eraser(self):
        candidates = self._eraser_candidates
        self._eraser_candidates = {}
        self._eraser_active = False
        if not candidates:
            self.eraser_trail.finish()
            return
        self.undo_stack.beginMacro('Erase drawing marks')
        for item, indexes in candidates.items():
            before = copy.deepcopy(item.strokes)
            after = [
                stroke for index, stroke in enumerate(before)
                if index not in indexes
            ]
            item.set_erase_preview(())
            if item is self.draw_item:
                item.replace_strokes(after)
                continue
            if after:
                item.replace_strokes(after)
                self.undo_stack.push(commands.ChangeDrawing(
                    item, after, before, ignore_first_redo=True))
            else:
                item.replace_strokes(before)
                self.undo_stack.push(commands.DeleteItems(
                    self.scene, [item]))
        self.undo_stack.endMacro()
        self.eraser_trail.finish()

    def _begin_mark(self, scene_pos):
        if self.draw_item is None:
            self._new_drawing_at(scene_pos)
        local_pos = self.draw_item.mapFromScene(scene_pos)
        point = {
            'x': round(local_pos.x(), 2),
            'y': round(local_pos.y(), 2),
            'pressure': max(0.05, self._tablet_pressure),
        }
        self.draw_current_stroke = {
            'tool': self.draw_tool,
            'style': self.draw_style,
            'color': list(self.draw_brush_color),
            'base_size': self.draw_brush_size,
            'points': [point],
        }
        self.draw_item.prepareGeometryChange()
        self.draw_item.temp_stroke = self.draw_current_stroke
        self.draw_item.update()

    def on_items_loaded(self, value):
        logger.debug('On items loaded: add queued items')
        self.scene.add_queued_items()

    def on_loading_finished(self, filename, errors):
        if errors:
            QtWidgets.QMessageBox.warning(
                self,
                'Problem loading file',
                ('<p>Problem loading file %s</p>'
                 '<p>Not accessible or not a proper bee file</p>') % filename)
        else:
            self.filename = filename
            self.scene.add_queued_items()
            self.on_action_fit_scene()

    def on_action_open_recent_file(self, filename):
        confirm = self.get_confirmation_unsaved_changes(
            'There are unsaved changes. '
            'Are you sure you want to open a new scene?')
        if confirm:
            self.open_from_file(filename)

    def open_from_file(self, filename):
        logger.info(f'Opening file {filename}')
        self.clear_scene()
        self.worker = fileio.ThreadedIO(
            fileio.load_bee, filename, self.scene)
        self.worker.progress.connect(self.on_items_loaded)
        self.worker.finished.connect(self.on_loading_finished)
        self.progress = widgets.BeeProgressDialog(
            f'Loading {filename}',
            worker=self.worker,
            parent=self)
        self.worker.start()

    def on_action_open(self):
        confirm = self.get_confirmation_unsaved_changes(
            'There are unsaved changes. '
            'Are you sure you want to open a new scene?')
        if not confirm:
            return

        self.cancel_active_modes()
        filename, f = QtWidgets.QFileDialog.getOpenFileName(
            parent=self,
            caption='Open file',
            filter=f'{constants.APPNAME} File (*.bee)')
        if filename:
            filename = os.path.normpath(filename)
            self.open_from_file(filename)
            self.filename = filename

    def on_saving_finished(self, filename, errors):
        if errors:
            QtWidgets.QMessageBox.warning(
                self,
                'Problem saving file',
                ('<p>Problem saving file %s</p>'
                 '<p>File/directory not accessible</p>') % filename)
        else:
            self.filename = filename
            self.undo_stack.setClean()

    def do_save(self, filename, create_new):
        if not fileio.is_bee_file(filename):
            filename = f'{filename}.bee'
        self.worker = fileio.ThreadedIO(
            fileio.save_bee, filename, self.scene, create_new=create_new)
        self.worker.finished.connect(self.on_saving_finished)
        self.progress = widgets.BeeProgressDialog(
            f'Saving {filename}',
            worker=self.worker,
            parent=self)
        self.worker.start()

    def on_action_save_as(self):
        self.cancel_active_modes()
        directory = os.path.dirname(self.filename) if self.filename else None
        filename, f = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption='Save file',
            directory=directory,
            filter=f'{constants.APPNAME} File (*.bee)')
        if filename:
            self.do_save(filename, create_new=True)

    def on_action_save(self):
        self.cancel_active_modes()
        if not self.filename:
            self.on_action_save_as()
        else:
            self.do_save(self.filename, create_new=False)

    def on_action_export_scene(self):
        directory = os.path.dirname(self.filename) if self.filename else None
        filename, formatstr = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption='Export Scene to Image',
            directory=directory,
            filter=';;'.join(('Image Files (*.png *.jpg *.jpeg *.svg)',
                              'PNG (*.png)',
                              'JPEG (*.jpg *.jpeg)',
                              'SVG (*.svg)')))

        if not filename:
            return

        name, ext = os.path.splitext(filename)
        if not ext:
            ext = get_file_extension_from_format(formatstr)
            filename = f'{filename}.{ext}'
        logger.debug(f'Got export filename {filename}')

        exporter_cls = exporter_registry[ext]
        exporter = exporter_cls(self.scene)
        if not exporter.get_user_input(self):
            return

        self.worker = fileio.ThreadedIO(exporter.export, filename)
        self.worker.finished.connect(self.on_export_finished)
        self.progress = widgets.BeeProgressDialog(
            f'Exporting {filename}',
            worker=self.worker,
            parent=self)
        self.worker.start()

    def on_export_finished(self, filename, errors):
        if errors:
            err_msg = '</br>'.join(str(errors))
            QtWidgets.QMessageBox.warning(
                self,
                'Problem writing file',
                f'<p>Problem writing file {filename}</p><p>{err_msg}</p>')

    def on_action_export_images(self):
        directory = os.path.dirname(self.filename) if self.filename else None
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            parent=self,
            caption='Export Images',
            directory=directory)

        if not directory:
            return

        logger.debug(f'Got export directory {directory}')
        self.exporter = ImagesToDirectoryExporter(self.scene, directory)
        self.worker = fileio.ThreadedIO(self.exporter.export)
        self.worker.user_input_required.connect(
            self.on_export_images_file_exists)
        self.worker.finished.connect(self.on_export_finished)
        self.progress = widgets.BeeProgressDialog(
            f'Exporting to {directory}',
            worker=self.worker,
            parent=self)
        self.worker.start()

    def on_export_images_file_exists(self, filename):
        dlg = widgets.ExportImagesFileExistsDialog(self, filename)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.exporter.handle_existing = dlg.get_answer()
            directory = self.exporter.dirname
            self.progress = widgets.BeeProgressDialog(
                f'Exporting to {directory}',
                worker=self.worker,
                parent=self)
            self.worker.start()

    def on_action_quit(self):
        confirm = self.get_confirmation_unsaved_changes(
            'You still have unsaved changes in the current scene. '
            'Do you want to save them before exiting?')
        if confirm:
            logger.info('User quit. Exiting...')
            self.app.quit()

    def on_action_settings(self):
        widgets.settings.SettingsDialog(self)

    def on_action_keyboard_settings(self):
        widgets.controls.ControlsDialog(self)

    def on_action_help(self):
        widgets.HelpDialog(self)

    def on_action_about(self):
        widgets.AboutDialog(self)

    def on_action_debuglog(self):
        widgets.DebugLogDialog(self)

    def on_insert_images_finished(self, new_scene, filename, errors):
        """Callback for when loading of images is finished.

        :param new_scene: True if the scene was empty before, else False
        :param filename: Not used, for compatibility only
        :param errors: List of filenames that couldn't be loaded
        """

        logger.debug('Insert images finished')
        if errors:
            errornames = [
                f'<li>{fn}</li>' for fn in errors]
            errornames = '<ul>%s</ul>' % '\n'.join(errornames)
            num = len(errors)
            msg = f'{num} image(s) could not be opened.<br/>'
            QtWidgets.QMessageBox.warning(
                self,
                'Problem loading images',
                msg + IMG_LOADING_ERROR_MSG + errornames)
        self.scene.add_queued_items()
        self.scene.arrange_default()
        self.undo_stack.endMacro()
        if new_scene:
            self.on_action_fit_scene()
        inserted = len(self.scene.selectedItems(user_only=True))
        if inserted:
            self.show_feedback(
                f'Added {inserted} image{"s" if inserted != 1 else ""}',
                '▣', 'insert_images')

    def do_insert_images(self, filenames, pos=None):
        if not pos:
            pos = self.get_view_center()
        self.scene.deselect_all_items()
        self.undo_stack.beginMacro('Insert Images')
        self.worker = fileio.ThreadedIO(
            fileio.load_images,
            filenames,
            self.mapToScene(pos),
            self.scene)
        self.worker.progress.connect(self.on_items_loaded)
        self.worker.finished.connect(
            partial(self.on_insert_images_finished,
                    not self.scene.items()))
        self.progress = widgets.BeeProgressDialog(
            'Loading images',
            worker=self.worker,
            parent=self)
        self.worker.start()

    def on_action_insert_images(self):
        self.cancel_active_modes()
        formats = self.get_supported_image_formats(QtGui.QImageReader)
        logger.debug(f'Supported image types for reading: {formats}')
        filenames, f = QtWidgets.QFileDialog.getOpenFileNames(
            parent=self,
            caption='Select one or more images to open',
            filter=f'Images ({formats})')
        self.do_insert_images(filenames)

    def on_action_insert_text(self):
        # Keep the color picker available while draw mode owns focus.
        if self.active_mode == self.DRAW_MODE:
            self.on_action_set_brush_color()
            return
        self.cancel_active_modes()
        item = BeeTextItem()
        pos = self.mapToScene(self.mapFromGlobal(self.cursor().pos()))
        item.setScale(1 / self.get_scale())
        self.undo_stack.push(commands.InsertItems(self.scene, [item], pos))
        self.show_feedback('Note added', '✎', 'insert_text')

    def on_action_copy(self):
        logger.debug('Copying to clipboard...')
        self.cancel_active_modes()
        clipboard = QtWidgets.QApplication.clipboard()
        items = self.scene.selectedItems(user_only=True)

        # At the moment, we can only copy one image to the global
        # clipboard. (Later, we might create an image of the whole
        # selection for external copying.)
        items[0].copy_to_clipboard(clipboard)

        # However, we can copy all items to the internal clipboard:
        self.scene.copy_selection_to_internal_clipboard()

        # We set a marker for ourselves in the global clipboard so
        # that we know to look up the internal clipboard when pasting:
        clipboard.mimeData().setData(
            'beeref/items', QtCore.QByteArray.number(len(items)))
        self.show_feedback(
            f'Copied {len(items)} item{"s" if len(items) != 1 else ""}',
            '⎘', 'copy')

    def on_action_paste(self):
        self.cancel_active_modes()
        logger.debug('Pasting from clipboard...')
        clipboard = QtWidgets.QApplication.clipboard()
        pos = self.mapToScene(self.mapFromGlobal(self.cursor().pos()))

        # See if we need to look up the internal clipboard:
        mime_data = clipboard.mimeData()
        data = (mime_data.data('beeref/items')
                if mime_data is not None else QtCore.QByteArray())
        logger.debug(f'Custom data in clipboard: {data}')
        if data and self.scene.internal_clipboard:
            # Checking that internal clipboard exists since the user
            # may have opened a new scene since copying.
            self.scene.paste_from_internal_clipboard(pos)
            self.show_feedback('Pasted items', '⎘', 'paste')
            return

        img = clipboard.image()
        if not img.isNull():
            item = BeePixmapItem(img)
            self.undo_stack.push(commands.InsertItems(self.scene, [item], pos))
            if len(self.scene.items()) == 1:
                # This is the first image in the scene
                self.on_action_fit_scene()
            self.show_feedback('Pasted image', '▣', 'paste')
            return
        text = clipboard.text()
        if text:
            item = BeeTextItem(text)
            item.setScale(1 / self.get_scale())
            self.undo_stack.push(commands.InsertItems(self.scene, [item], pos))
            self.show_feedback('Pasted note', '✎', 'paste')
            return

        msg = 'No image data or text in clipboard or image too big'
        logger.info(msg)
        self.show_feedback(msg, '!', 'paste', duration=2400)

    def on_action_open_settings_dir(self):
        dirname = os.path.dirname(self.settings.fileName())
        QtGui.QDesktopServices.openUrl(
            QtCore.QUrl.fromLocalFile(dirname))

    def on_selection_changed(self):
        try:
            selected_items = self.scene.selectedItems(user_only=True)
        except RuntimeError:
            # Qt can emit a final selection signal while tearing down the
            # graphics scene during application exit.
            return
        logger.debug('Currently selected items: %s',
                     len(selected_items))
        self.actiongroup_set_enabled('active_when_selection',
                                     bool(selected_items))
        self.actiongroup_set_enabled('active_when_single_image',
                                     len(selected_items) == 1
                                     and selected_items[0].is_image)

        if selected_items:
            item = selected_items[0]
            grayscale = getattr(item, 'grayscale', False)
            self._syncing_actions = True
            try:
                actions.actions['grayscale'].qaction.setChecked(grayscale)
            finally:
                self._syncing_actions = False
        self.viewport().repaint()

    def on_cursor_changed(self, cursor):
        if self.active_mode is None:
            self.viewport().setCursor(cursor)

    def on_cursor_cleared(self):
        if self.active_mode is None:
            self.viewport().unsetCursor()

    def recalc_scene_rect(self):
        """Keep several screens of navigable space around the viewport."""

        if self.previous_transform or self._recalculating_scene_rect:
            return
        logger.trace('Recalculating scene rectangle...')
        self._recalculating_scene_rect = True
        try:
            visible = self.mapToScene(self.viewport().rect()).boundingRect()
            canvas = QtCore.QRectF(self.scene.used_space_rect)
            combined = visible if canvas.isEmpty() else visible.united(canvas)
            margin_x = max(visible.width() * 4, 1000)
            margin_y = max(visible.height() * 4, 1000)
            self.setSceneRect(combined.marginsAdded(
                QtCore.QMarginsF(margin_x, margin_y, margin_x, margin_y)))
        except OverflowError:
            logger.info('Maximum scene size reached')
        finally:
            self._recalculating_scene_rect = False
        logger.trace('Done recalculating scene rectangle')

    def drawBackground(self, painter, rect):
        from beeref.theme import canvas_colors

        theme = self.settings.valueOrDefault('Appearance/theme')
        dead_color, used_color = canvas_colors(theme)
        painter.fillRect(rect, QtGui.QColor(dead_color))
        used = self.scene.used_space_rect.intersected(rect)
        if not used.isNull() and not used.isEmpty():
            painter.fillRect(used, QtGui.QColor(used_color))

    def get_zoom_size(self, func):
        """Calculates the size of all items' bounding box in the view's
        coordinates.

        This helps ensure that we never zoom out too much (scene
        becomes so tiny that items become invisible) or zoom in too
        much (causing overflow errors).

        :param func: Function which takes the width and height as
            arguments and turns it into a number, for ex. ``min`` or ``max``.
        """

        topleft = self.mapFromScene(
            self.scene.itemsBoundingRect().topLeft())
        bottomright = self.mapFromScene(
            self.scene.itemsBoundingRect().bottomRight())
        return func(bottomright.x() - topleft.x(),
                    bottomright.y() - topleft.y())

    def scale(self, *args, **kwargs):
        super().scale(*args, **kwargs)
        self.scene.on_view_scale_change()
        self.recalc_scene_rect()

    def get_scale(self):
        return self.transform().m11()

    def pan(self, delta):
        hscroll = self.horizontalScrollBar()
        hscroll.setValue(int(hscroll.value() + delta.x()))
        vscroll = self.verticalScrollBar()
        vscroll.setValue(int(vscroll.value() + delta.y()))
        self.recalc_scene_rect()

    def zoom(self, delta, anchor):
        # We calculate where the anchor is before and after the zoom
        # and then move the view accordingly to keep the anchor fixed
        # We can't use QGraphicsView's AnchorUnderMouse since it
        # uses the current cursor position while we need the initial mouse
        # press position for zooming with Ctrl + Middle Drag
        anchor = QtCore.QPoint(round(anchor.x()),
                               round(anchor.y()))
        ref_point = self.mapToScene(anchor)
        if delta == 0:
            return
        step = 1 + abs(delta / 1000)
        factor = step if delta > 0 else 1 / step
        current = self.get_scale()
        if ((delta > 0 and current >= 10000.0)
                or (delta < 0 and current <= 0.0001)):
            return
        target = max(0.0001, min(10000.0, current * factor))
        factor = target / current
        if abs(factor - 1) < 1e-12:
            return
        self.scale(factor, factor)

        self.pan(self.mapFromScene(ref_point) - anchor)
        self.reset_previous_transform()

    def wheelEvent(self, event):
        action, inverted\
            = self.keyboard_settings.mousewheel_action_for_event(event)

        delta = event.angleDelta().y()
        if delta == 0:
            # Precision trackpads commonly provide pixel deltas while wheels
            # provide angle deltas.
            delta = event.pixelDelta().y() * 8
        if inverted:
            delta = delta * -1

        if action == 'zoom':
            self.zoom(delta, event.position())
            event.accept()
            return
        if action == 'pan_horizontal':
            self.pan(QtCore.QPointF(0, 0.5 * delta))
            event.accept()
            return
        if action == 'pan_vertical':
            self.pan(QtCore.QPointF(0.5 * delta, 0))
            event.accept()
            return

    def viewportEvent(self, event):
        if event.type() == QtCore.QEvent.Type.NativeGesture:
            gesture = event.gestureType()
            if gesture == Qt.NativeGestureType.ZoomNativeGesture:
                # QNativeGestureEvent.value() is a small incremental scale
                # delta. Reuse the same mouse-anchored zoom path as wheels.
                self.zoom(float(event.value()) * 900, event.position())
                event.accept()
                return True
            if gesture in (Qt.NativeGestureType.BeginNativeGesture,
                           Qt.NativeGestureType.EndNativeGesture):
                event.accept()
                return True
        return super().viewportEvent(event)

    def tabletEvent(self, event):
        if self.active_mode == self.DRAW_MODE:
            self._tablet_pressure = event.pressure()
            # Don't accept — let Qt synthesize mouse events for drawing
            event.ignore()
        else:
            super().tabletEvent(event)

    def event(self, event):
        # Claim draw-mode shortcuts before the global QAction shortcuts.
        if (event.type() == QtCore.QEvent.Type.ShortcutOverride
                and getattr(self, 'active_mode', None) == self.DRAW_MODE
                and event.key() in (
                    Qt.Key.Key_D, Qt.Key.Key_L, Qt.Key.Key_R, Qt.Key.Key_C,
                    Qt.Key.Key_E, Qt.Key.Key_T, Qt.Key.Key_1, Qt.Key.Key_2,
                    Qt.Key.Key_3, Qt.Key.Key_BracketLeft,
                    Qt.Key.Key_BracketRight, Qt.Key.Key_Meta,
                    Qt.Key.Key_Control)):
            event.accept()
            return True
        return super().event(event)

    def mousePressEvent(self, event):
        if (event.button() == Qt.MouseButton.RightButton
                and self.parent.isFullScreen()
                and not sys.platform.startswith('win')):
            self._right_canvas_pending = True
            self._right_canvas_panning = False
            self.event_start = event.position()
            event.accept()
            return

        if (event.button() == Qt.MouseButton.RightButton
                and self.mousePressEventMainControls(event)):
            return

        if self.active_mode == self.DRAW_MODE:
            modifiers = event.modifiers()
            if (event.button() == Qt.MouseButton.MiddleButton
                    or (event.button() == Qt.MouseButton.LeftButton
                        and modifiers
                        & Qt.KeyboardModifier.AltModifier)):
                self._draw_panning = True
                self.event_start = event.position()
                self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
                event.accept()
                return
            if event.button() == Qt.MouseButton.LeftButton:
                if (sys.platform == 'darwin'
                        and self.draw_tool == 'pen'
                        and modifiers
                        & Qt.KeyboardModifier.ControlModifier):
                    self._temporary_eraser_tool = 'pen'
                    self.set_draw_tool('eraser', announce=False)
                scene_pos = self.mapToScene(event.pos())
                if self.draw_tool == 'eraser':
                    self._begin_eraser(scene_pos, event.position())
                else:
                    self._begin_mark(scene_pos)
                event.accept()
                return
            return super().mousePressEvent(event)

        if self.mousePressEventMainControls(event):
            return

        if self.active_mode == self.SAMPLE_COLOR_MODE:
            if (event.button() == Qt.MouseButton.LeftButton):
                color = self.scene.sample_color_at(
                    self.mapToScene(event.pos()))
                if color:
                    name = qcolor_to_hex(color)
                    clipboard = QtWidgets.QApplication.clipboard()
                    clipboard.setText(name)
                    self.scene.internal_clipboard = []
                    msg = f'Copied color to clipboard: {name}'
                    logger.debug(msg)
                    self.show_feedback(msg, '◉', 'sample_color')
                else:
                    logger.debug('No color found')
            self.cancel_sample_color_mode()
            event.accept()
            return

        action, inverted = self.keyboard_settings.mouse_action_for_event(event)

        if action == 'zoom':
            self.active_mode = self.ZOOM_MODE
            self.event_start = event.position()
            self.event_anchor = event.position()
            self.event_inverted = inverted
            event.accept()
            return

        if action == 'pan':
            logger.trace('Begin pan')
            self.active_mode = self.PAN_MODE
            self.event_start = event.position()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            # ClosedHandCursor and OpenHandCursor don't work, but I
            # don't know if that's only on my system or a general
            # problem. It works with other cursors.
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._right_canvas_pending:
            pos = event.position()
            if ((pos - self.event_start).manhattanLength() >= 6
                    or self._right_canvas_panning):
                if not self._right_canvas_panning:
                    self._right_canvas_panning = True
                    self.viewport().setCursor(
                        Qt.CursorShape.ClosedHandCursor)
                self.reset_previous_transform()
                self.pan(self.event_start - pos)
                self.event_start = pos
            event.accept()
            return

        if self._right_canvas_panning:
            self.reset_previous_transform()
            pos = event.position()
            self.pan(self.event_start - pos)
            self.event_start = pos
            event.accept()
            return

        if self.active_mode == self.DRAW_MODE and self._draw_panning:
            self.reset_previous_transform()
            pos = event.position()
            self.pan(self.event_start - pos)
            self.event_start = pos
            event.accept()
            return

        if (self.active_mode == self.DRAW_MODE
                and self.draw_tool == 'eraser'
                and event.buttons() & Qt.MouseButton.LeftButton):
            self._preview_erase_at(
                self.mapToScene(event.pos()), event.position())
            event.accept()
            return

        if (self.active_mode == self.DRAW_MODE
                and self.draw_current_stroke is not None):
            scene_pos = self.mapToScene(event.pos())
            local_pos = self.draw_item.mapFromScene(scene_pos)
            start = BeePathItem._point(
                self.draw_current_stroke['points'][0])
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                local_pos = self._constrained_point(
                    start, local_pos, self.draw_tool)
            point = {
                'x': round(local_pos.x(), 2),
                'y': round(local_pos.y(), 2),
                'pressure': self._tablet_pressure,
            }
            self.draw_item.prepareGeometryChange()
            points = self.draw_current_stroke['points']
            if self.draw_tool == 'pen' and not (
                    event.modifiers()
                    & Qt.KeyboardModifier.ShiftModifier):
                previous = BeePathItem._point(points[-1])
                sample_distance = max(
                    0.25,
                    1.2 / max(self.get_scale() * self.draw_item.scale(),
                              0.0001))
                if ((local_pos - previous).manhattanLength()
                        >= sample_distance):
                    points.append(point)
            elif len(points) == 1:
                points.append(point)
            else:
                points[-1] = point
            self.draw_item.temp_stroke = self.draw_current_stroke
            self.draw_item.update()
            event.accept()
            return

        if self.active_mode == self.PAN_MODE:
            self.reset_previous_transform()
            pos = event.position()
            self.pan(self.event_start - pos)
            self.event_start = pos
            event.accept()
            return

        if self.active_mode == self.ZOOM_MODE:
            self.reset_previous_transform()
            pos = event.position()
            delta = (self.event_start - pos).y()
            if self.event_inverted:
                delta *= -1
            self.event_start = pos
            self.zoom(delta * 20, self.event_anchor)
            event.accept()
            return

        if self.active_mode == self.SAMPLE_COLOR_MODE:
            self.sample_color_widget.update(
                event.position(),
                self.scene.sample_color_at(self.mapToScene(event.pos())))
            event.accept()
            return

        if self.mouseMoveEventMainControls(event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._right_canvas_pending:
            was_panning = self._right_canvas_panning
            self._right_canvas_pending = False
            self._right_canvas_panning = False
            self.viewport().unsetCursor()
            if self.active_mode == self.DRAW_MODE:
                self.set_draw_tool(self.draw_tool, announce=False)
            if not was_panning:
                self.on_context_menu(event.position().toPoint())
            event.accept()
            return
        if self.active_mode == self.DRAW_MODE and self._draw_panning:
            self._draw_panning = False
            self.set_draw_tool(self.draw_tool)
            event.accept()
            return
        if (self.active_mode == self.DRAW_MODE
                and self._eraser_active
                and event.button() == Qt.MouseButton.LeftButton):
            self._commit_eraser()
            event.accept()
            return
        if (self.active_mode == self.DRAW_MODE
                and self.draw_current_stroke is not None):
            self.draw_item.add_stroke(self.draw_current_stroke)
            self.draw_item.temp_stroke = None
            self.draw_current_stroke = None
            self._tablet_pressure = 1.0
            if not self._draw_editing_existing:
                completed_item = self.draw_item
                self.scene.removeItem(completed_item)
                self.undo_stack.push(commands.InsertItems(
                    self.scene, [completed_item]))
                self.draw_item = None
            event.accept()
            return

        if self.active_mode == self.PAN_MODE:
            logger.trace('End pan')
            self.viewport().unsetCursor()
            self.active_mode = None
            event.accept()
            return
        if self.active_mode == self.ZOOM_MODE:
            self.active_mode = None
            event.accept()
            return
        if self.mouseReleaseEventMainControls(event):
            return
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.recalc_scene_rect()
        if self._fullscreen_anchor is not None:
            self._restore_global_canvas_anchor(*self._fullscreen_anchor)
        self.welcome_overlay.resize(self.size())
        if hasattr(self, 'draw_toolbar'):
            self._position_draw_toolbar()
        if hasattr(self, 'eraser_trail'):
            self.eraser_trail.setGeometry(self.viewport().rect())
        if hasattr(self, 'window_chrome'):
            self.window_chrome.reposition()
        if getattr(self, '_hud_toast', None) is not None:
            self._hud_toast.reposition()

    def keyPressEvent(self, event):
        if self.keyPressEventMainControls(event):
            return
        if self.active_mode == self.DRAW_MODE:
            modifiers = event.modifiers()
            if (sys.platform == 'darwin'
                    and event.key() in (Qt.Key.Key_Control, Qt.Key.Key_Meta)
                    and not event.isAutoRepeat()
                    and self.draw_tool == 'pen'):
                self._temporary_eraser_tool = self.draw_tool
                self.set_draw_tool('eraser', announce=False)
                event.accept()
                return
            if (event.key() == Qt.Key.Key_D
                    and modifiers & Qt.KeyboardModifier.ControlModifier):
                self.exit_draw_mode(commit=True)
                event.accept()
                return
            if (event.key() == Qt.Key.Key_T
                    and modifiers & Qt.KeyboardModifier.ControlModifier):
                self.on_action_set_brush_color()
                event.accept()
                return
            tool_keys = {
                Qt.Key.Key_D: 'pen',
                Qt.Key.Key_L: 'line',
                Qt.Key.Key_R: 'rectangle',
                Qt.Key.Key_C: 'ellipse',
                Qt.Key.Key_E: 'eraser',
            }
            style_keys = {
                Qt.Key.Key_1: 'solid',
                Qt.Key.Key_2: 'dotted',
                Qt.Key.Key_3: 'arrow',
            }
            if (modifiers == Qt.KeyboardModifier.NoModifier
                    and event.key() in tool_keys):
                self.set_draw_tool(tool_keys[event.key()])
                event.accept()
                return
            if (modifiers == Qt.KeyboardModifier.NoModifier
                    and event.key() in style_keys):
                self.set_draw_style(style_keys[event.key()])
                event.accept()
                return
            if event.key() in (Qt.Key.Key_BracketLeft,
                               Qt.Key.Key_BracketRight):
                delta = -1 if event.key() == Qt.Key.Key_BracketLeft else 1
                self.draw_toolbar.set_width(self.draw_brush_size + delta)
                event.accept()
                return
            if event.key() == Qt.Key.Key_Escape:
                self.exit_draw_mode(commit=True)
                event.accept()
                return
        if self.active_mode == self.SAMPLE_COLOR_MODE:
            self.cancel_sample_color_mode()
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if (self.active_mode == self.DRAW_MODE
                and self._temporary_eraser_tool is not None
                and event.key() in (Qt.Key.Key_Control, Qt.Key.Key_Meta)
                and not event.isAutoRepeat()):
            previous = self._temporary_eraser_tool
            self._temporary_eraser_tool = None
            self.set_draw_tool(previous, announce=False)
            event.accept()
            return
        super().keyReleaseEvent(event)
