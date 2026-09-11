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

import logging
import sys

from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import Qt

from beeref import commands, widgets
from beeref.items import BeePixmapItem
from beeref import fileio


logger = logging.getLogger(__name__)


class MainControlsMixin:
    """Basic controls shared by the main view and the welcome overlay:

    * Right-click menu
    * Dropping files
    * Moving the window without title bar
    """

    def init_main_controls(self, main_window):
        self.main_window = main_window
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(
            self.control_target.on_context_menu)
        self.setAcceptDrops(True)
        self.movewin_active = False
        self.right_window_drag_active = False
        self.right_window_dragged = False

    def on_action_movewin_mode(self):
        if self.movewin_active:
            # Pressing the same shortcut again should end the action
            self.exit_movewin_mode()
        else:
            self.enter_movewin_mode()

    @property
    def viewport_or_self(self):
        if hasattr(self, 'viewport'):
            return self.viewport()
        return self

    def enter_movewin_mode(self):
        logger.debug('Entering movewin mode')
        self.setMouseTracking(True)
        self.movewin_active = True
        self.viewport_or_self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.event_start = QtCore.QPointF(self.cursor().pos())
        if hasattr(self, 'disable_mouse_events'):
            self.disable_mouse_events()

    def exit_movewin_mode(self):
        logger.debug('Exiting movewin mode')
        self.setMouseTracking(False)
        self.movewin_active = False
        self.viewport_or_self.unsetCursor()
        if hasattr(self, 'enable_mouse_events'):
            self.enable_mouse_events()

    def dragEnterEvent(self, event):
        mimedata = event.mimeData()
        logger.debug(f'Drag enter event: {mimedata.formats()}')
        if mimedata.hasUrls():
            event.acceptProposedAction()
        elif mimedata.hasImage():
            event.acceptProposedAction()
        else:
            msg = 'Attempted drop not an image or image too big'
            logger.info(msg)
            if hasattr(self.control_target, 'show_feedback'):
                self.control_target.show_feedback(msg, '!', duration=2400)
            else:
                widgets.BeeNotification(self.control_target, msg)

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        mimedata = event.mimeData()
        logger.debug(f'Handling file drop: {mimedata.formats()}')
        pos = QtCore.QPoint(round(event.position().x()),
                            round(event.position().y()))
        if mimedata.hasUrls():
            logger.debug(f'Found dropped urls: {mimedata.urls()}')
            if not self.control_target.scene.items():
                # Check if we have a bee file we can open directly
                path = mimedata.urls()[0]
                if (path.isLocalFile()
                        and fileio.is_bee_file(path.toLocalFile())):
                    self.control_target.open_from_file(path.toLocalFile())
                    return
            self.control_target.do_insert_images(mimedata.urls(), pos)
        elif mimedata.hasImage():
            img = QtGui.QImage(mimedata.imageData())
            item = BeePixmapItem(img)
            pos = self.control_target.mapToScene(pos)
            self.control_target.undo_stack.push(
                commands.InsertItems(self.control_target.scene, [item], pos))
        else:
            logger.info('Drop not an image')

    def mousePressEventMainControls(self, event):
        if self.movewin_active:
            self.exit_movewin_mode()
            event.accept()
            return True

        target = self.control_target
        fullscreen = bool(target.parent.isFullScreen())
        locked = getattr(target, 'window_position_locked', False)
        if (event.button() == Qt.MouseButton.RightButton
                and fullscreen and not locked
                and sys.platform.startswith('win')):
            # On Windows a right-drag tears the fullscreen canvas back into
            # a movable window and keeps it attached to the pointer.
            from beeref.actions import actions

            fullscreen_action = actions.actions['fullscreen'].qaction
            if fullscreen_action and fullscreen_action.isChecked():
                fullscreen_action.setChecked(False)
            else:
                target.parent.showNormal()
            fullscreen = False
        if (event.button() == Qt.MouseButton.RightButton
                and not fullscreen and not locked):
            self.right_window_drag_active = True
            self.right_window_dragged = False
            self.event_start = event.globalPosition()
            self._right_window_origin = self.main_window.pos()
            self.viewport_or_self.setCursor(Qt.CursorShape.SizeAllCursor)
            event.accept()
            return True

        action, inverted =\
            self.control_target.keyboard_settings.mouse_action_for_event(event)
        if action == 'movewindow':
            self.enter_movewin_mode()
            event.accept()
            return True

    def mouseMoveEventMainControls(self, event):
        if self.right_window_drag_active:
            current = event.globalPosition().toPoint()
            delta = current - self.event_start.toPoint()
            if delta.manhattanLength() >= 3:
                self.right_window_dragged = True
            self.main_window.move(self._right_window_origin + delta)
            event.accept()
            return True
        if self.movewin_active:
            pos = self.mapToGlobal(event.position())
            delta = pos - self.event_start
            self.event_start = pos
            self.main_window.move(self.main_window.x() + int(delta.x()),
                                  self.main_window.y() + int(delta.y()))
            event.accept()
            return True

    def mouseReleaseEventMainControls(self, event):
        if self.right_window_drag_active:
            was_dragged = self.right_window_dragged
            self.right_window_drag_active = False
            self.right_window_dragged = False
            self.viewport_or_self.unsetCursor()
            if not was_dragged:
                point = event.position().toPoint()
                if self is not self.control_target:
                    point = self.mapTo(self.control_target, point)
                self.control_target.on_context_menu(point)
            event.accept()
            return True
        if self.movewin_active:
            self.exit_movewin_mode()
            event.accept()
            return True

    def keyPressEventMainControls(self, event):
        if self.movewin_active:
            self.exit_movewin_mode()
            event.accept()
            return True
