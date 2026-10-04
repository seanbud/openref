#!/usr/bin/env python3

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
import os
import platform
import signal
import sys

from PyQt6 import QtCore, QtWidgets

from beeref import constants
from beeref.assets import BeeAssets
from beeref.config import CommandlineArgs, BeeSettings, logfile_name
from beeref.utils import create_palette_from_dict
from beeref.view import BeeGraphicsView
from beeref.theme import apply_theme

logger = logging.getLogger(__name__)


class BeeRefApplication(QtWidgets.QApplication):

    def event(self, event):
        if event.type() == QtCore.QEvent.Type.FileOpen:
            for widget in self.topLevelWidgets():
                if isinstance(widget, BeeRefMainWindow):
                    widget.view.open_from_file(event.file())
                    return True
            return False
        else:
            return super().event(event)


class BeeRefMainWindow(QtWidgets.QMainWindow):

    _RESIZE_MARGIN = 8
    _MINIMUM_RESIZE_SIZE = QtCore.QSize(320, 220)

    def __init__(self, app):
        super().__init__()
        self.setObjectName('openRefWindow')
        app.setOrganizationName(constants.APPNAME)
        app.setApplicationName(constants.APPNAME)
        app.setApplicationDisplayName(constants.APPNAME)
        app.setDesktopFileName('org.openref.OpenRef')
        # Keep the asset owner alive for the lifetime of the native window
        # icon. Setting QApplication's global icon is redundant here and
        # crashes Qt's offscreen Linux plugin after repeated test windows.
        self.assets = BeeAssets()
        self.setWindowIcon(self.assets.logo)
        self.setContentsMargins(1, 1, 1, 1)
        self._resize_drag = None
        self._resize_hovering = False
        self._resize_surface = None
        self.view = BeeGraphicsView(app, self)
        default_window_size = QtCore.QSize(500, 300)
        geom = self.view.settings.value('MainWindow/geometry')
        if geom is None:
            self.resize(default_window_size)
        else:
            if not self.restoreGeometry(geom):
                self.resize(default_window_size)
        self.setCentralWidget(self.view)
        # Qt's native resize hit-test is unreliable for a frameless window on
        # Windows after showNormal() restores it from fullscreen. Keep a
        # small client-side edge zone so fullscreen restoration always leaves
        # a normally resizable window, without affecting regular title-bar
        # windows or maximized/fullscreen states.
        self._resize_surfaces = [
            self.view.viewport(), self.view.window_chrome,
            *self.view.window_chrome.findChildren(QtWidgets.QWidget),
        ]
        for surface in self._resize_surfaces:
            surface.setMouseTracking(True)
            surface.installEventFilter(self)
        self.show()

    def _resize_edges_at(self, global_pos):
        if (self.isFullScreen() or self.isMaximized()
                or not (self.windowFlags()
                        & QtCore.Qt.WindowType.FramelessWindowHint)):
            return QtCore.Qt.Edge(0)
        rect = self.frameGeometry()
        margin = self._RESIZE_MARGIN
        edges = QtCore.Qt.Edge(0)
        if global_pos.x() <= rect.left() + margin:
            edges |= QtCore.Qt.Edge.LeftEdge
        elif global_pos.x() >= rect.right() - margin:
            edges |= QtCore.Qt.Edge.RightEdge
        if global_pos.y() <= rect.top() + margin:
            edges |= QtCore.Qt.Edge.TopEdge
        elif global_pos.y() >= rect.bottom() - margin:
            edges |= QtCore.Qt.Edge.BottomEdge
        return edges

    @staticmethod
    def _resize_cursor(edges):
        horizontal = QtCore.Qt.Edge.LeftEdge | QtCore.Qt.Edge.RightEdge
        vertical = QtCore.Qt.Edge.TopEdge | QtCore.Qt.Edge.BottomEdge
        if edges & horizontal and edges & vertical:
            if ((edges & QtCore.Qt.Edge.LeftEdge
                 and edges & QtCore.Qt.Edge.TopEdge)
                    or (edges & QtCore.Qt.Edge.RightEdge
                        and edges & QtCore.Qt.Edge.BottomEdge)):
                return QtCore.Qt.CursorShape.SizeFDiagCursor
            return QtCore.Qt.CursorShape.SizeBDiagCursor
        if edges & horizontal:
            return QtCore.Qt.CursorShape.SizeHorCursor
        return QtCore.Qt.CursorShape.SizeVerCursor

    def _apply_resize_drag(self, global_pos):
        start_rect, start_pos, edges = self._resize_drag
        dx = global_pos.x() - start_pos.x()
        dy = global_pos.y() - start_pos.y()
        rect = QtCore.QRect(start_rect)
        minimum = self.minimumSize().expandedTo(self._MINIMUM_RESIZE_SIZE)
        if edges & QtCore.Qt.Edge.LeftEdge:
            rect.setLeft(min(
                rect.left() + dx, rect.right() - minimum.width() + 1))
        if edges & QtCore.Qt.Edge.RightEdge:
            rect.setRight(max(
                rect.right() + dx, rect.left() + minimum.width() - 1))
        if edges & QtCore.Qt.Edge.TopEdge:
            rect.setTop(min(
                rect.top() + dy, rect.bottom() - minimum.height() + 1))
        if edges & QtCore.Qt.Edge.BottomEdge:
            rect.setBottom(max(
                rect.bottom() + dy, rect.top() + minimum.height() - 1))
        self.setGeometry(rect)

    def eventFilter(self, watched, event):
        if watched in getattr(self, '_resize_surfaces', ()):
            kind = event.type()
            if kind in (QtCore.QEvent.Type.MouseMove,
                        QtCore.QEvent.Type.MouseButtonPress,
                        QtCore.QEvent.Type.MouseButtonRelease):
                global_pos = watched.mapToGlobal(event.position().toPoint())
                if self._resize_drag is not None:
                    if (kind == QtCore.QEvent.Type.MouseMove
                            and (event.buttons()
                                 & QtCore.Qt.MouseButton.LeftButton)):
                        self._apply_resize_drag(global_pos)
                        event.accept()
                        return True
                    if (kind == QtCore.QEvent.Type.MouseButtonRelease
                            and (event.button()
                                 == QtCore.Qt.MouseButton.LeftButton)):
                        self._resize_drag = None
                        self._resize_hovering = False
                        if self._resize_surface is not None:
                            self._resize_surface.unsetCursor()
                        self._resize_surface = None
                        event.accept()
                        return True
                edges = self._resize_edges_at(global_pos)
                if (kind == QtCore.QEvent.Type.MouseButtonPress
                        and event.button() == QtCore.Qt.MouseButton.LeftButton
                        and edges):
                    self._resize_drag = (QtCore.QRect(self.geometry()),
                                         global_pos, edges)
                    watched.setCursor(self._resize_cursor(edges))
                    self._resize_surface = watched
                    event.accept()
                    return True
                if kind == QtCore.QEvent.Type.MouseMove:
                    if edges:
                        watched.setCursor(self._resize_cursor(edges))
                        self._resize_hovering = True
                    elif self._resize_hovering:
                        watched.unsetCursor()
                        self._resize_hovering = False
                        self._resize_surface = None
        return super().eventFilter(watched, event)

    def closeEvent(self, event):
        geom = self.saveGeometry()
        self.view.settings.setValue('MainWindow/geometry', geom)
        event.accept()

    def __del__(self):
        if hasattr(self, 'view'):
            del self.view


def safe_timer(timeout, func, *args, **kwargs):
    """Create a timer that is safe against garbage collection and
    overlapping calls.
    See: http://ralsina.me/weblog/posts/BB974.html
    """
    def timer_event():
        try:
            func(*args, **kwargs)
        finally:
            QtCore.QTimer.singleShot(timeout, timer_event)
    QtCore.QTimer.singleShot(timeout, timer_event)


def handle_sigint(signum, frame):
    logger.info('Received interrupt. Exiting...')
    QtWidgets.QApplication.quit()


def handle_uncaught_exception(exc_type, exc, traceback):
    logger.critical('Unhandled exception',
                    exc_info=(exc_type, exc, traceback))
    QtWidgets.QApplication.quit()


sys.excepthook = handle_uncaught_exception


def main():
    logger.info(f'Starting {constants.APPNAME} version {constants.VERSION}')
    logger.debug('System: %s', ' '.join(platform.uname()))
    logger.debug('Python: %s', platform.python_version())
    logger.debug('LD_LIBRARY_PATH: %s', os.environ.get('LD_LIBRARY_PATH'))
    args = CommandlineArgs(with_check=True)  # Force checking
    settings = BeeSettings()
    logger.info(f'Using settings: {settings.fileName()}')
    logger.info(f'Logging to: {logfile_name()}')
    settings.on_startup()
    assert not args.debug_raise_error, args.debug_raise_error

    os.environ["QT_DEBUG_PLUGINS"] = "1"
    app = BeeRefApplication(sys.argv)
    apply_theme(app, settings.valueOrDefault('Appearance/theme'))
    palette = create_palette_from_dict(constants.COLORS)
    app.setPalette(palette)
    bee = BeeRefMainWindow(app)  # NOQA:F841

    signal.signal(signal.SIGINT, handle_sigint)
    # Repeatedly run python-noop to give the interpreter time to
    # handle signals
    safe_timer(50, lambda: None)
    if args.smoke_test is True:
        QtCore.QTimer.singleShot(500, app.quit)

    app.exec()
    del bee
    del app
    logger.debug('OpenRef closed')
    QtCore.qInstallMessageHandler(None)


if __name__ == '__main__':
    main()  # pragma: no cover
