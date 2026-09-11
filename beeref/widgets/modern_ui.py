"""OpenRef canvas dialogs and optional frameless-window controls."""

# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright © 2026 Sean Budning and OpenRef contributors.

from PyQt6 import QtCore, QtGui, QtWidgets


Qt = QtCore.Qt


class ColorPickerDialog(QtWidgets.QColorDialog):
    """Use Qt's established picker while previewing stroke color live."""

    color_changed = QtCore.pyqtSignal(QtGui.QColor)

    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Choose stroke color')
        self.setOption(
            QtWidgets.QColorDialog.ColorDialogOption.ShowAlphaChannel, True)
        self.setOption(
            QtWidgets.QColorDialog.ColorDialogOption.DontUseNativeDialog,
            True)
        self.currentColorChanged.connect(self.color_changed.emit)
        self.set_color(color)

    def set_color(self, color):
        self.setCurrentColor(QtGui.QColor(color))


class ChromeButton(QtWidgets.QToolButton):
    """Minimal vector button for OpenRef's optional canvas window bar."""

    def __init__(self, kind, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setFixedSize(28, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(kind == 'pin')

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.scale(self.width() / 36, self.height() / 36)
        pen = QtGui.QPen(QtGui.QColor('#e9e9eb'), 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        if self.kind == 'close':
            painter.drawLine(11, 11, 25, 25)
            painter.drawLine(25, 11, 11, 25)
        elif self.kind == 'minimize':
            painter.drawLine(11, 22, 25, 22)
        elif self.kind == 'maximize':
            painter.drawRoundedRect(QtCore.QRectF(11, 11, 14, 14), 1, 1)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor('#e9e9eb'))
            pin = QtGui.QPainterPath()
            pin.moveTo(13, 9)
            pin.lineTo(23, 9)
            pin.lineTo(21, 14)
            pin.lineTo(24, 19)
            pin.lineTo(19, 20)
            pin.lineTo(18, 29)
            pin.lineTo(16, 20)
            pin.lineTo(11, 19)
            pin.lineTo(15, 14)
            pin.closeSubpath()
            painter.drawPath(pin)
            if not self.isChecked():
                painter.setPen(QtGui.QPen(QtGui.QColor('#242424'), 2.2))
                painter.drawLine(11, 9, 26, 25)


class WindowChrome(QtWidgets.QFrame):
    """Window controls for user-selected frameless canvas mode."""

    def __init__(self, parent, window, pin_callback, close_callback=None,
                 hover_targets=()):
        super().__init__(parent)
        self.window = window
        self._enabled = False
        self._drag_origin = None
        self._window_origin = None
        self.setObjectName('windowChrome')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMouseTracking(True)
        self.setFixedHeight(34)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(2)
        self.close_button = ChromeButton('close', self)
        self.close_button.clicked.connect(close_callback or window.close)
        layout.addWidget(self.close_button)
        self.minimize_button = ChromeButton('minimize', self)
        self.minimize_button.clicked.connect(window.showMinimized)
        layout.addWidget(self.minimize_button)
        self.maximize_button = ChromeButton('maximize', self)
        self.maximize_button.clicked.connect(self._toggle_maximized)
        layout.addWidget(self.maximize_button)
        self.pin_button = ChromeButton('pin', self)
        self.pin_button.clicked.connect(pin_callback)
        layout.addWidget(self.pin_button)
        layout.addStretch(1)

        self.opacity = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity)
        self.fade = QtCore.QPropertyAnimation(self.opacity, b'opacity', self)
        self.fade.setDuration(180)
        self.fade.finished.connect(self._hide_if_transparent)
        self.hide_timer = QtCore.QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.fade_out)
        for target in hover_targets:
            target.setMouseTracking(True)
            target.installEventFilter(self)
        self.hide()

    def set_enabled(self, enabled):
        self._enabled = enabled
        if not enabled:
            self.hide()

    def set_pinned(self, pinned):
        self.pin_button.setChecked(pinned)
        self.pin_button.update()

    def reposition(self):
        self.setGeometry(0, 0, self.parentWidget().width(), 34)

    def reveal(self):
        if not self._enabled:
            return
        self.fade.stop()
        self.opacity.setOpacity(1.0)
        self.reposition()
        self.show()
        self.raise_()
        self.hide_timer.start(1300)

    def fade_out(self):
        if not self.isVisible() or self.underMouse():
            return
        self.fade.stop()
        self.fade.setStartValue(self.opacity.opacity())
        self.fade.setEndValue(0.0)
        self.fade.start()

    def _hide_if_transparent(self):
        if self.opacity.opacity() <= 0.01:
            self.hide()

    def _toggle_maximized(self):
        if self.window.isMaximized():
            self.window.showNormal()
        else:
            self.window.showMaximized()

    def enterEvent(self, event):
        self.hide_timer.stop()
        self.reveal()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hide_timer.start(500)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event.globalPosition().toPoint()
            self._window_origin = self.window.pos()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (self._drag_origin is not None
                and event.buttons() & Qt.MouseButton.LeftButton):
            delta = event.globalPosition().toPoint() - self._drag_origin
            self.window.move(self._window_origin + delta)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_origin = None
        self._window_origin = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximized()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.Type.MouseMove:
            if event.position().y() <= 24:
                self.reveal()
        return super().eventFilter(watched, event)


class UnsavedChangesDialog(QtWidgets.QDialog):
    """Conventional native-framed save confirmation with three outcomes."""

    CANCEL = 0
    DISCARD = 1
    SAVE = 2

    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Unsaved changes')
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumWidth(430)

        heading = QtWidgets.QLabel('Save changes to this board?', self)
        heading.setObjectName('dialogTitle')
        self.message = QtWidgets.QLabel(message, self)
        self.message.setObjectName('dialogMessage')
        self.message.setWordWrap(True)

        icon = QtWidgets.QLabel('●', self)
        icon.setObjectName('unsavedStatusIcon')
        icon.setAlignment(Qt.AlignmentFlag.AlignTop
                          | Qt.AlignmentFlag.AlignHCenter)
        content = QtWidgets.QGridLayout()
        content.setHorizontalSpacing(14)
        content.addWidget(icon, 0, 0, 2, 1)
        content.addWidget(heading, 0, 1)
        content.addWidget(self.message, 1, 1)

        self.remember = QtWidgets.QCheckBox(
            'Use this choice for the rest of this session', self)
        buttons = QtWidgets.QDialogButtonBox(self)
        save = buttons.addButton(
            'Save', QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        discard = buttons.addButton(
            "Don't Save",
            QtWidgets.QDialogButtonBox.ButtonRole.DestructiveRole)
        cancel = buttons.addButton(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        save.clicked.connect(lambda: self.done(self.SAVE))
        discard.clicked.connect(lambda: self.done(self.DISCARD))
        cancel.clicked.connect(lambda: self.done(self.CANCEL))

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 14)
        layout.setSpacing(14)
        layout.addLayout(content)
        layout.addWidget(self.remember)
        layout.addWidget(buttons)

    @classmethod
    def get_choice(cls, parent, message):
        dialog = cls(message, parent)
        result = dialog.exec()
        return result, dialog.remember.isChecked()
