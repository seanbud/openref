"""Quiet, selection-driven rich-text controls for canvas notes."""

# SPDX-License-Identifier: GPL-3.0-or-later

from PyQt6 import QtCore, QtGui, QtWidgets

from beeref.config import BeeSettings
from beeref.widgets.modern_ui import _ColorChannel, _SaturationValueField


Qt = QtCore.Qt


class _NoteColorPopover(QtWidgets.QFrame):
    """Small live color studio, anchored at the user's current pointer."""

    color_changed = QtCore.pyqtSignal(QtGui.QColor)
    hover_changed = QtCore.pyqtSignal()

    MAX_COLORS = 12
    COLUMNS = 6
    RECENT_COLORS_KEY = 'Drawing/recent_colors'
    PINNED_COLORS_KEY = 'Drawing/pinned_colors'
    STARTER_COLORS = (
        '#F3F4F6', '#FFD166', '#FF789A', '#EF476F', '#F77F4A', '#42D6A4',
        '#32B8E6', '#6C8CFF', '#B794F6', '#B6E36B', '#F2A65A', '#E5E7EB',
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('noteColorPopover')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.settings = BeeSettings()
        self._color = QtGui.QColor('#f3f4f6')

        self.field = _SaturationValueField(self)
        self.field.setFixedSize(178, 96)
        self.field.color_changed.connect(self._field_changed)
        self.hue = _ColorChannel('hue', self)
        self.hue.setFixedWidth(178)
        self.hue.value_changed.connect(self._hue_changed)

        self.swatches = QtWidgets.QWidget(self)
        self.swatch_layout = QtWidgets.QGridLayout(self.swatches)
        self.swatch_layout.setContentsMargins(0, 0, 0, 0)
        self.swatch_layout.setHorizontalSpacing(4)
        self.swatch_layout.setVerticalSpacing(4)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(self.field)
        layout.addWidget(self.hue)
        layout.addWidget(self.swatches)
        self.setFixedWidth(194)
        self._refresh_swatches()
        self.set_color(self._color, emit=False)
        self.hide()

    @staticmethod
    def _color_key(color):
        return QtGui.QColor(color).name(
            QtGui.QColor.NameFormat.HexArgb).upper()

    def _load_colors(self, key):
        values = self.settings.value(key, [], type=list) or []
        result = []
        for value in values:
            color = QtGui.QColor(value)
            if color.isValid():
                value = self._color_key(color)
                if value not in result:
                    result.append(value)
        return result[:self.MAX_COLORS]

    def _save_colors(self, key, values):
        self.settings.setValue(key, values[:self.MAX_COLORS])

    def _clear_swatches(self):
        while self.swatch_layout.count():
            item = self.swatch_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

    def _colors_for_grid(self):
        pinned = self._load_colors(self.PINNED_COLORS_KEY)
        recent = self._load_colors(self.RECENT_COLORS_KEY)
        choices = []
        for value in (*pinned, *recent, *self.STARTER_COLORS):
            value = self._color_key(value)
            if value not in choices:
                choices.append(value)
        return choices[:self.MAX_COLORS]

    def _refresh_swatches(self):
        self._clear_swatches()
        pinned = set(self._load_colors(self.PINNED_COLORS_KEY))
        for index, value in enumerate(self._colors_for_grid()):
            button = QtWidgets.QToolButton(self.swatches)
            button.setObjectName('noteColorSwatch')
            button.setFixedSize(25, 18)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(
                'QToolButton { background: ' + value + '; border: 1px solid '
                'rgba(255, 255, 255, 45); border-radius: 4px; } '
                'QToolButton:hover { border: 1px solid #ffffff; }')
            label = 'Pinned' if value in pinned else 'Recent color'
            button.setToolTip(f'{label}: {value}\nRight-click to '
                              f'{"unpin" if value in pinned else "pin"}')
            button.clicked.connect(
                lambda checked, choice=value: self._choose_swatch(choice))
            button.setContextMenuPolicy(
                Qt.ContextMenuPolicy.CustomContextMenu)
            button.customContextMenuRequested.connect(
                lambda point, choice=value, is_pinned=value in pinned:
                self._set_pinned(choice, not is_pinned))
            self.swatch_layout.addWidget(
                button, index // self.COLUMNS, index % self.COLUMNS)

    def _set_pinned(self, value, pinned):
        value = self._color_key(value)
        colors = self._load_colors(self.PINNED_COLORS_KEY)
        if pinned:
            colors = [value, *[item for item in colors if item != value]]
        else:
            colors = [item for item in colors if item != value]
        self._save_colors(self.PINNED_COLORS_KEY, colors)
        self._refresh_swatches()

    def _remember(self, color):
        value = self._color_key(color)
        colors = self._load_colors(self.RECENT_COLORS_KEY)
        colors = [value, *[item for item in colors if item != value]]
        self._save_colors(self.RECENT_COLORS_KEY, colors)

    def _choose_swatch(self, color):
        self.set_color(color)
        self._remember(color)
        self._refresh_swatches()

    def _field_changed(self, color):
        color.setAlpha(255)
        self.set_color(color)

    def _hue_changed(self, hue):
        color = QtGui.QColor.fromHsvF(
            hue, self.field.saturation, self.field.value, 1.0)
        self.set_color(color)

    def set_color(self, color, emit=True):
        color = QtGui.QColor(color)
        if not color.isValid():
            return
        color.setAlpha(255)
        self._color = color
        hue = color.hsvHueF()
        self.field.set_color(color)
        self.hue.set_value(hue if hue >= 0 else self.hue.value)
        if emit:
            self.color_changed.emit(QtGui.QColor(color))

    def show_for(self, anchor, avoid_rect=None):
        """Place beside a toolbar without obscuring the selected note."""
        parent = self.parentWidget()
        if parent is None:
            return
        self._refresh_swatches()
        self.adjustSize()
        anchor_rect = anchor.geometry()
        width, height = self.width(), self.height()
        bounds = parent.rect().adjusted(6, 6, -6, -6)
        candidates = (
            (anchor_rect.center().x() - width // 2,
             anchor_rect.top() - height - 7),
            (anchor_rect.right() + 8,
             anchor_rect.center().y() - height // 2),
            (anchor_rect.left() - width - 8,
             anchor_rect.center().y() - height // 2),
            (anchor_rect.center().x() - width // 2,
             anchor_rect.bottom() + 8),
        )
        placed = []
        for x, y in candidates:
            x = max(bounds.left(), min(x, bounds.right() - width + 1))
            y = max(bounds.top(), min(y, bounds.bottom() - height + 1))
            rect = QtCore.QRect(x, y, width, height)
            placed.append(rect)
            if avoid_rect is None or not rect.intersects(avoid_rect):
                self.move(rect.topLeft())
                break
        else:
            # A very small viewport can leave no perfect answer. Pick the
            # least-overlapping candidate rather than blindly covering text.
            def overlap(rect):
                intersection = rect.intersected(avoid_rect)
                return intersection.width() * intersection.height()

            self.move(min(placed, key=overlap).topLeft())
        self.show()
        self.raise_()

    def hideEvent(self, event):
        self._remember(self._color)
        super().hideEvent(event)

    def enterEvent(self, event):
        self.hover_changed.emit()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_changed.emit()
        super().leaveEvent(event)


class NoteToolbar(QtWidgets.QFrame):
    """A deliberately small toolbar shown only for hovered selected text."""

    format_requested = QtCore.pyqtSignal(str, object)
    hover_changed = QtCore.pyqtSignal()

    _FORMATS = ('bold', 'italic', 'underline', 'strike')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('noteToolbar')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._state = {name: False for name in self._FORMATS}
        self._state['color'] = QtGui.QColor('#f3f4f6')
        self._build_ui()
        self._apply_style()
        self.hide()

    def _build_ui(self):
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(1)
        self.format_buttons = {}
        labels = {'bold': 'B', 'italic': 'I', 'underline': 'U',
                  'strike': 'S'}
        for kind in self._FORMATS:
            button = QtWidgets.QToolButton(self)
            button.setObjectName(f'noteFormat{kind.title()}')
            button.setText(labels[kind])
            button.setCheckable(True)
            button.setFixedSize(25, 24)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            font = button.font()
            if kind == 'bold':
                font.setBold(True)
            elif kind == 'italic':
                font.setItalic(True)
            elif kind == 'underline':
                font.setUnderline(True)
            else:
                font.setStrikeOut(True)
            button.setFont(font)
            button.setToolTip(kind.capitalize())
            button.clicked.connect(
                lambda checked, name=kind: self._format(name, checked))
            self.format_buttons[kind] = button
            layout.addWidget(button)

        self.text_color_button = QtWidgets.QToolButton(self)
        self.text_color_button.setObjectName('noteTextColor')
        self.text_color_button.setText('●')
        self.text_color_button.setToolTip('Text color')
        self.text_color_button.setFixedSize(27, 24)
        self.text_color_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.text_color_button.clicked.connect(self._choose_text_color)
        layout.addWidget(self.text_color_button)
        self.buttons = self.format_buttons

        self.color_popover = _NoteColorPopover(self.parentWidget())
        self.color_popover.color_changed.connect(
            lambda color: self._format('color', color))
        self.color_popover.hover_changed.connect(self.hover_changed)

    def _apply_style(self):
        self.setStyleSheet('''
            QFrame#noteToolbar {
                background: palette(window); border: 1px solid palette(mid);
                border-radius: 6px;
            }
            QToolButton {
                min-height: 22px; border: 0; border-radius: 4px;
                padding: 0 4px;
            }
            QToolButton:hover { background: rgba(127, 127, 127, 45); }
            QToolButton:checked { background: rgba(90, 140, 210, 110); }
            QToolButton#noteTextColor { font-size: 16px; }
        ''')
        self.color_popover.setStyleSheet('''
            QFrame#noteColorPopover {
                background: palette(window); border: 1px solid palette(mid);
                border-radius: 7px;
            }
        ''')
        self._refresh_color_button()

    def _refresh_color_button(self):
        color = QtGui.QColor(self._state['color'])
        self.text_color_button.setStyleSheet(
            'QToolButton#noteTextColor { color: '
            f'{color.name(QtGui.QColor.NameFormat.HexRgb)}; }}')

    def _format(self, kind, value):
        self._state[kind] = value
        self.format_requested.emit(kind, value)

    def set_state(self, state):
        """Update controls from the current selected text without emitting."""
        state = state or {}
        self._state.update({key: state[key] for key in self._FORMATS
                            if key in state})
        for key in self._FORMATS:
            button = self.format_buttons[key]
            button.blockSignals(True)
            button.setChecked(bool(self._state[key]))
            button.blockSignals(False)
        if 'color' in state and QtGui.QColor(state['color']).isValid():
            self._state['color'] = QtGui.QColor(state['color'])
            self._refresh_color_button()

    def _choose_text_color(self):
        self.color_popover.set_color(self._state['color'], emit=False)
        self.color_popover.show_for(
            self, getattr(self, '_note_rect', None))

    def reposition_for_rect(self, note_rect):
        """Place near the selected note, constrained to the viewport."""
        viewport = self.parentWidget()
        if viewport is None:
            return
        self.adjustSize()
        rect = QtCore.QRect(note_rect)
        self._note_rect = QtCore.QRect(rect)
        x = rect.center().x() - self.width() // 2
        x = max(6, min(x, viewport.width() - self.width() - 6))
        above = rect.top() - self.height() - 6
        below = rect.bottom() + 6
        y = above if above >= 6 else below
        y = max(6, min(y, viewport.height() - self.height() - 6))
        self.move(x, y)

    def hide_popovers(self):
        self.color_popover.hide()

    def is_hovered(self):
        return self.underMouse() or self.color_popover.underMouse()

    def enterEvent(self, event):
        self.hover_changed.emit()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_changed.emit()
        super().leaveEvent(event)
