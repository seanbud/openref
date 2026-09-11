"""OpenRef canvas dialogs and optional frameless-window controls."""

# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright © 2026 Sean Budning and OpenRef contributors.

from PyQt6 import QtCore, QtGui, QtWidgets


Qt = QtCore.Qt


class _ColorChannel(QtWidgets.QWidget):
    """A compact painted color channel with a draggable round handle."""

    value_changed = QtCore.pyqtSignal(float)

    def __init__(self, mode, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.value = 0.0 if mode == 'hue' else 1.0
        self.color = QtGui.QColor('#ffffff')
        self.setFixedHeight(18)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def sizeHint(self):
        return QtCore.QSize(280, 18)

    def set_value(self, value):
        self.value = max(0.0, min(1.0, float(value)))
        self.update()

    def set_color(self, color):
        self.color = QtGui.QColor(color)
        self.update()

    def _update_from_position(self, position):
        width = max(1, self.width() - 10)
        self.set_value((position.x() - 5) / width)
        self.value_changed.emit(self.value)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._update_from_position(event.position())
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._update_from_position(event.position())
            event.accept()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        track = QtCore.QRectF(5, 5, self.width() - 10, 8)
        if self.mode == 'hue':
            gradient = QtGui.QLinearGradient(track.topLeft(),
                                             track.topRight())
            for offset, color in (
                    (0.0, '#ff3b52'), (0.16, '#ffd43b'),
                    (0.33, '#36db6b'), (0.50, '#28d7db'),
                    (0.67, '#3b78ff'), (0.84, '#c546ef'),
                    (1.0, '#ff3b52')):
                gradient.setColorAt(offset, QtGui.QColor(color))
        else:
            tile = 4
            for y in range(5, 13, tile):
                for x in range(5, self.width() - 5, tile):
                    tone = '#6c6f76' if ((x + y) // tile) % 2 else '#3d4046'
                    painter.fillRect(x, y, tile, tile, QtGui.QColor(tone))
            transparent = QtGui.QColor(self.color)
            transparent.setAlpha(0)
            opaque = QtGui.QColor(self.color)
            opaque.setAlpha(255)
            gradient = QtGui.QLinearGradient(track.topLeft(),
                                             track.topRight())
            gradient.setColorAt(0, transparent)
            gradient.setColorAt(1, opaque)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(track, 4, 4)
        handle_x = track.left() + track.width() * self.value
        painter.setBrush(QtGui.QColor('#ffffff'))
        painter.setPen(QtGui.QPen(QtGui.QColor('#16171a'), 1))
        painter.drawEllipse(QtCore.QPointF(handle_x, 9), 5, 5)


class _SaturationValueField(QtWidgets.QWidget):
    """Two-dimensional saturation/value field rendered without bitmaps."""

    color_changed = QtCore.pyqtSignal(QtGui.QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hue = 0.0
        self.saturation = 0.0
        self.value = 1.0
        self.alpha = 1.0
        self.setMinimumSize(300, 190)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def set_color(self, color):
        color = QtGui.QColor(color)
        hue = color.hsvHueF()
        if hue >= 0:
            self.hue = hue
        self.saturation = color.hsvSaturationF()
        self.value = color.valueF()
        self.alpha = color.alphaF()
        self.update()

    def current_color(self):
        return QtGui.QColor.fromHsvF(
            self.hue, self.saturation, self.value, self.alpha)

    def _update_from_position(self, position):
        self.saturation = max(
            0.0, min(1.0, position.x() / max(1, self.width())))
        self.value = 1.0 - max(
            0.0, min(1.0, position.y() / max(1, self.height())))
        self.update()
        self.color_changed.emit(self.current_color())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._update_from_position(event.position())
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._update_from_position(event.position())
            event.accept()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        rect = QtCore.QRectF(self.rect()).adjusted(0, 0, -1, -1)
        hue_color = QtGui.QColor.fromHsvF(self.hue, 1, 1)
        horizontal = QtGui.QLinearGradient(rect.topLeft(), rect.topRight())
        horizontal.setColorAt(0, QtGui.QColor('#ffffff'))
        horizontal.setColorAt(1, hue_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(horizontal)
        painter.drawRoundedRect(rect, 10, 10)
        vertical = QtGui.QLinearGradient(rect.topLeft(), rect.bottomLeft())
        vertical.setColorAt(0, QtGui.QColor(0, 0, 0, 0))
        vertical.setColorAt(1, QtGui.QColor(0, 0, 0, 255))
        painter.setBrush(vertical)
        painter.drawRoundedRect(rect, 10, 10)
        marker = QtCore.QPointF(
            rect.left() + self.saturation * rect.width(),
            rect.top() + (1 - self.value) * rect.height())
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QtGui.QPen(QtGui.QColor('#ffffff'), 2))
        painter.drawEllipse(marker, 6, 6)
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 150), 1))
        painter.drawEllipse(marker, 7.5, 7.5)


class ColorPickerDialog(QtWidgets.QDialog):
    """Original compact HSV picker with live toolbar preview."""

    color_changed = QtCore.pyqtSignal(QtGui.QColor)

    SWATCHES = (
        '#f6d365', '#f58aa8', '#ea526f', '#fa704c',
        '#5ac8a8', '#39a8e8', '#7776df', '#f4f1ea',
    )

    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.setObjectName('colorDialog')
        self.setWindowTitle('Stroke color')
        self.setWindowFlags(Qt.WindowType.Dialog
                            | Qt.WindowType.FramelessWindowHint)
        # Frameless dialogs do not reliably paint their stylesheet background
        # unless this is explicit (notably on macOS with a translucent parent).
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setModal(True)
        self.setFixedWidth(352)
        self._color = QtGui.QColor(color)
        self._updating = False
        self._drag_origin = None
        self._window_origin = None

        title = QtWidgets.QLabel('Stroke color', self)
        title.setObjectName('colorDialogHeader')
        title.setCursor(Qt.CursorShape.SizeAllCursor)
        title.installEventFilter(self)
        close = QtWidgets.QToolButton(self)
        close.setObjectName('dialogClose')
        close.setText('×')
        close.setFixedSize(26, 26)
        close.clicked.connect(self.reject)
        header = QtWidgets.QHBoxLayout()
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(close)

        self.field = _SaturationValueField(self)
        self.field.color_changed.connect(self._field_changed)
        self.hue = _ColorChannel('hue', self)
        self.hue.value_changed.connect(self._hue_changed)
        self.alpha = _ColorChannel('alpha', self)
        self.alpha.value_changed.connect(self._alpha_changed)

        self.preview = QtWidgets.QLabel(self)
        self.preview.setObjectName('colorPreview')
        self.preview.setFixedSize(34, 34)
        self.hex_edit = QtWidgets.QLineEdit(self)
        self.hex_edit.setObjectName('colorHex')
        self.hex_edit.setMaxLength(7)
        self.hex_edit.editingFinished.connect(self._hex_changed)
        self.opacity = QtWidgets.QSpinBox(self)
        self.opacity.setObjectName('colorOpacity')
        self.opacity.setRange(0, 100)
        self.opacity.setSuffix('%')
        self.opacity.valueChanged.connect(self._opacity_changed)
        values = QtWidgets.QHBoxLayout()
        values.setSpacing(8)
        values.addWidget(self.preview)
        values.addWidget(self.hex_edit, 1)
        values.addWidget(self.opacity)

        swatches = QtWidgets.QHBoxLayout()
        swatches.setSpacing(6)
        self.swatch_buttons = []
        for value in self.SWATCHES:
            button = QtWidgets.QToolButton(self)
            button.setObjectName('colorSwatch')
            button.setCheckable(True)
            button.setFixedSize(30, 30)
            button.setStyleSheet(
                f'QToolButton {{ background: {value}; }}')
            button.clicked.connect(
                lambda checked, choice=value: self.set_color(
                    QtGui.QColor(choice)))
            self.swatch_buttons.append(button)
            swatches.addWidget(button)

        cancel = QtWidgets.QPushButton('Cancel', self)
        cancel.setObjectName('secondaryButton')
        cancel.clicked.connect(self.reject)
        apply = QtWidgets.QPushButton('Apply', self)
        apply.setObjectName('primaryButton')
        apply.clicked.connect(self.accept)
        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(apply)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        layout.addLayout(header)
        layout.addWidget(self.field)
        layout.addWidget(self.hue)
        layout.addWidget(self.alpha)
        layout.addLayout(values)
        layout.addLayout(swatches)
        layout.addSpacing(2)
        layout.addLayout(buttons)
        self.set_color(color, emit=False)

    def eventFilter(self, watched, event):
        if watched.objectName() == 'colorDialogHeader':
            if (event.type() == QtCore.QEvent.Type.MouseButtonPress
                    and event.button() == Qt.MouseButton.LeftButton):
                self._drag_origin = event.globalPosition().toPoint()
                self._window_origin = self.pos()
                event.accept()
                return True
            if (event.type() == QtCore.QEvent.Type.MouseMove
                    and self._drag_origin is not None
                    and event.buttons() & Qt.MouseButton.LeftButton):
                delta = event.globalPosition().toPoint() - self._drag_origin
                self.move(self._window_origin + delta)
                event.accept()
                return True
            if event.type() == QtCore.QEvent.Type.MouseButtonRelease:
                self._drag_origin = None
                self._window_origin = None
                event.accept()
                return True
        return super().eventFilter(watched, event)

    def currentColor(self):
        return QtGui.QColor(self._color)

    def selectedColor(self):
        return self.currentColor()

    def _publish(self, color):
        if self._updating:
            return
        self.set_color(color)

    def _field_changed(self, color):
        color.setAlphaF(self.alpha.value)
        self._publish(color)

    def _hue_changed(self, hue):
        color = QtGui.QColor.fromHsvF(
            hue, self.field.saturation, self.field.value,
            self.alpha.value)
        self._publish(color)

    def _alpha_changed(self, alpha):
        color = QtGui.QColor(self._color)
        color.setAlphaF(alpha)
        self._publish(color)

    def _hex_changed(self):
        color = QtGui.QColor(self.hex_edit.text())
        if color.isValid():
            color.setAlpha(self._color.alpha())
            self._publish(color)
        else:
            self.hex_edit.setText(self._color.name().upper())

    def _opacity_changed(self, value):
        color = QtGui.QColor(self._color)
        color.setAlphaF(value / 100)
        self._publish(color)

    def set_color(self, color, emit=True):
        color = QtGui.QColor(color)
        if not color.isValid():
            return
        self._updating = True
        self._color = color
        hue = color.hsvHueF()
        self.field.set_color(color)
        self.hue.set_value(hue if hue >= 0 else self.hue.value)
        self.alpha.set_color(color)
        self.alpha.set_value(color.alphaF())
        self.hex_edit.setText(color.name().upper())
        self.opacity.setValue(round(color.alphaF() * 100))
        self.preview.setStyleSheet(
            f'background: {color.name(QtGui.QColor.NameFormat.HexArgb)}; '
            'border-radius: 17px;')
        for button, swatch in zip(self.swatch_buttons, self.SWATCHES):
            button.setChecked(color.name().lower() == swatch)
        self._updating = False
        if emit:
            self.color_changed.emit(QtGui.QColor(color))


class EraserTrailOverlay(QtWidgets.QWidget):
    """Soft transient viewport trail used while staging an erase gesture."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.points = []
        self.radius = 8.0
        self.clock = QtCore.QElapsedTimer()
        self.refresh = QtCore.QTimer(self)
        self.refresh.setInterval(16)
        self.refresh.timeout.connect(self._age_points)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.fade = QtCore.QPropertyAnimation(self.effect, b'opacity', self)
        self.fade.setDuration(110)
        self.fade.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self.fade.finished.connect(self._clear_after_fade)
        self.hide()

    def begin(self, point, radius):
        self.fade.stop()
        self.effect.setOpacity(1.0)
        self.clock.start()
        self.points = [(QtCore.QPointF(point), 0)]
        self.radius = max(3.0, float(radius))
        if self.parentWidget():
            self.setGeometry(self.parentWidget().rect())
        self.show()
        self.refresh.start()
        self.update()

    def add_point(self, point):
        point = QtCore.QPointF(point)
        if not self.points or (
                point - self.points[-1][0]).manhattanLength() >= 2:
            self.points.append((point, self.clock.elapsed()))
            self.update()

    def _age_points(self):
        if not self.points:
            self.refresh.stop()
            return
        cutoff = self.clock.elapsed() - 170
        while len(self.points) > 2 and self.points[1][1] < cutoff:
            self.points.pop(0)
        self.update()

    def finish(self):
        if not self.points:
            return
        self.fade.stop()
        self.fade.setStartValue(self.effect.opacity())
        self.fade.setEndValue(0.0)
        self.fade.start()

    def cancel(self):
        self.fade.stop()
        self.refresh.stop()
        self.points = []
        self.hide()

    def _clear_after_fade(self):
        self.refresh.stop()
        self.points = []
        self.hide()

    def paintEvent(self, event):
        if not self.points:
            return
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        count = len(self.points)
        if count == 1:
            point = self.points[0][0]
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor(205, 209, 216, 95))
            painter.drawEllipse(point, self.radius, self.radius)
            return
        # Draw individual segments so the trail narrows and disappears
        # rapidly behind the eraser head instead of looking like a tube.
        for index in range(1, count):
            progress = index / max(1, count - 1)
            color = QtGui.QColor(194, 198, 205,
                                 round(18 + 105 * progress))
            pen = QtGui.QPen(color,
                             self.radius * (0.35 + 1.25 * progress))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(self.points[index - 1][0],
                             self.points[index][0])
        head = self.points[-1][0]
        painter.setBrush(QtGui.QColor(224, 226, 230, 60))
        painter.setPen(QtGui.QPen(QtGui.QColor(248, 249, 250, 130), 1))
        painter.drawEllipse(head, self.radius, self.radius)


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
        if event.type() == QtCore.QEvent.Type.Enter:
            self.reveal()
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
