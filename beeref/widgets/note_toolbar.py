"""Compact contextual controls for editing a note on the canvas."""

# SPDX-License-Identifier: GPL-3.0-or-later

from PyQt6 import QtCore, QtGui, QtWidgets

from beeref.widgets.modern_ui import ColorPickerDialog


Qt = QtCore.Qt


class NoteToolbar(QtWidgets.QFrame):
    """A small, viewport-owned toolbar which follows the active note.

    The toolbar deliberately owns no note model.  It reports user intent via
    ``format_requested`` and ``appearance_requested`` so callers can apply or
    undo changes in one place.
    """

    format_requested = QtCore.pyqtSignal(str, object)
    appearance_requested = QtCore.pyqtSignal(dict)

    _FORMATS = ('bold', 'italic', 'underline', 'strike')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('noteToolbar')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._state = {name: False for name in self._FORMATS}
        self._state.update(color=QtGui.QColor('#f3f4f6'), font_size=14)
        self._appearance = {
            'fill': QtGui.QColor('#fff4bf'),
            'border': QtGui.QColor('#5b4b2a'),
            'border_width': 1,
            'radius': 8,
        }
        self.color_dialog_open = False
        self._build_ui()
        self._apply_style()
        self.hide()

    def _build_ui(self):
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 3, 5, 3)
        layout.setSpacing(2)
        self.format_buttons = {}
        labels = {'bold': 'B', 'italic': 'I', 'underline': 'U',
                  'strike': 'S'}
        for kind in self._FORMATS:
            button = QtWidgets.QToolButton(self)
            button.setObjectName(f'noteFormat{kind.title()}')
            button.setText(labels[kind])
            button.setCheckable(True)
            button.setFixedSize(27, 26)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            font = button.font()
            if kind == 'bold':
                font.setBold(True)
            elif kind == 'italic':
                font.setItalic(True)
            elif kind == 'underline':
                font.setUnderline(True)
            elif kind == 'strike':
                font.setStrikeOut(True)
            button.setFont(font)
            button.setToolTip(kind.capitalize())
            button.clicked.connect(
                lambda checked, name=kind: self._format(name, checked))
            self.format_buttons[kind] = button
            layout.addWidget(button)

        self.text_color_button = QtWidgets.QToolButton(self)
        self.text_color_button.setObjectName('noteTextColor')
        self.text_color_button.setText('A')
        self.text_color_button.setToolTip('Text color')
        self.text_color_button.setFixedSize(28, 26)
        self.text_color_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.text_color_button.clicked.connect(self._choose_text_color)
        layout.addWidget(self.text_color_button)

        self.font_size_combo = QtWidgets.QComboBox(self)
        self.font_size_combo.setObjectName('noteFontSize')
        self.font_size_combo.addItems(['14', '18', '24', '32'])
        self.font_size_combo.setFixedSize(50, 26)
        self.font_size_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.font_size_combo.activated.connect(
            lambda index: self._format(
                'font_size', int(self.font_size_combo.itemText(index))))
        layout.addWidget(self.font_size_combo)

        self.text_width_spin = self._spin(120, 800, ' px')
        self.text_width_spin.setObjectName('noteTextWidth')
        self.text_width_spin.setValue(300)
        self.text_width_spin.setToolTip('Note text width')
        self.text_width_spin.valueChanged.connect(
            lambda value: self._format('text_width', value))

        self.appearance_button = QtWidgets.QPushButton('Appearance', self)
        self.appearance_button.setObjectName('noteAppearance')
        self.appearance_button.setFixedHeight(26)
        self.appearance_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.appearance_button.clicked.connect(self._toggle_appearance)
        layout.addWidget(self.appearance_button)
        # Public aliases keep integration simple and mirror the naming used by
        # the other canvas toolbars.
        self.buttons = self.format_buttons

        self.appearance_popover = QtWidgets.QFrame(self.parentWidget())
        self.appearance_popover.setObjectName('noteAppearancePopover')
        self.appearance_popover.setAttribute(
            Qt.WidgetAttribute.WA_StyledBackground, True)
        self.appearance_popover.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.appearance_popover.hide()
        pop = QtWidgets.QFormLayout(self.appearance_popover)
        pop.setContentsMargins(10, 8, 10, 10)
        pop.setSpacing(6)
        self.fill_color_button = self._color_button('Fill color', 'fill')
        self.border_color_button = self._color_button('Border color', 'border')
        pop.addRow('Fill', self.fill_color_button)
        pop.addRow('Border', self.border_color_button)
        self.border_width_spin = self._spin(0, 6, ' px')
        self.corner_radius_spin = self._spin(0, 24, ' px')
        pop.addRow('Border width', self.border_width_spin)
        pop.addRow('Corner radius', self.corner_radius_spin)
        pop.addRow('Text width', self.text_width_spin)
        self.border_width_spin.valueChanged.connect(
            lambda value: self._appearance_value('border_width', value))
        self.corner_radius_spin.valueChanged.connect(
            lambda value: self._appearance_value('radius', value))
        self.appearance_panel = self.appearance_popover

    @staticmethod
    def _spin(minimum, maximum, suffix):
        spin = QtWidgets.QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setSuffix(suffix)
        spin.setFixedWidth(85)
        spin.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return spin

    def _color_button(self, label, key):
        button = QtWidgets.QToolButton(self.appearance_popover)
        button.setObjectName(f'note{key.title()}Color')
        button.setText('')
        button.setToolTip(label)
        button.setFixedSize(48, 24)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.clicked.connect(lambda: self._choose_appearance_color(key))
        return button

    def _apply_style(self):
        style = '''
            QFrame#noteToolbar {
                background: palette(window); border: 1px solid palette(mid);
                border-radius: 7px;
            }
            QToolButton, QPushButton, QComboBox {
                min-height: 24px; border: 0; border-radius: 4px;
                padding: 1px 5px;
            }
            QToolButton:hover, QPushButton:hover, QComboBox:hover {
                background: rgba(127, 127, 127, 45);
            }
            QToolButton:checked { background: rgba(90, 140, 210, 110); }
            QToolButton#noteTextColor { border-bottom: 3px solid #f3f4f6; }
        '''
        self.setStyleSheet(style)
        # The appearance card is a sibling under the viewport, so the
        # toolbar stylesheet cannot reach it through Qt's parent selector.
        self.appearance_popover.setStyleSheet(
            'QFrame#noteAppearancePopover { background: palette(window); '
            'border: 1px solid palette(mid); border-radius: 7px; }'
        )
        self._refresh_color_buttons()

    def _format(self, kind, value):
        self._state[kind] = value
        self.format_requested.emit(kind, value)

    def set_state(self, state):
        """Update controls from a note state without emitting requests."""
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
            self._refresh_color_buttons()
        if 'font_size' in state:
            size = int(state['font_size'])
            self._state['font_size'] = size
            self.font_size_combo.blockSignals(True)
            self.font_size_combo.setCurrentText(str(size))
            self.font_size_combo.blockSignals(False)
        if 'text_width' in state:
            self.text_width_spin.blockSignals(True)
            self.text_width_spin.setValue(
                max(120, min(800, int(state['text_width'])))
            )
            self.text_width_spin.blockSignals(False)

    def set_appearance(self, appearance):
        """Update appearance controls without emitting a change signal."""
        appearance = appearance or {}
        # Accept both the concise model keys and explicit UI-facing names.
        appearance = dict(appearance)
        if 'fill_color' in appearance and 'fill' not in appearance:
            appearance['fill'] = appearance['fill_color']
        if 'border_color' in appearance and 'border' not in appearance:
            appearance['border'] = appearance['border_color']
        if 'corner_radius' in appearance and 'radius' not in appearance:
            appearance['radius'] = appearance['corner_radius']
        for key in ('fill', 'border'):
            if key in appearance and QtGui.QColor(appearance[key]).isValid():
                self._appearance[key] = QtGui.QColor(appearance[key])
        for key in ('border_width', 'radius'):
            if key in appearance:
                self._appearance[key] = max(0, int(appearance[key]))
        self.border_width_spin.blockSignals(True)
        self.border_width_spin.setValue(
            min(6, self._appearance['border_width']))
        self.border_width_spin.blockSignals(False)
        self.corner_radius_spin.blockSignals(True)
        self.corner_radius_spin.setValue(min(24, self._appearance['radius']))
        self.corner_radius_spin.blockSignals(False)
        self._refresh_color_buttons()

    def _refresh_color_buttons(self):
        color = QtGui.QColor(self._state['color'])
        self.text_color_button.setStyleSheet(
            'QToolButton#noteTextColor { border-bottom: 3px solid '
            f'{color.name(QtGui.QColor.NameFormat.HexArgb)}; }}')
        for key, button in (('fill', self.fill_color_button),
                            ('border', self.border_color_button)):
            value = self._appearance[key].name(
                QtGui.QColor.NameFormat.HexArgb)
            button.setStyleSheet(f'background: {value};')

    def _choose_text_color(self):
        self._choose_color(self._state['color'],
                           lambda color: self._format('color', color))

    def _choose_appearance_color(self, key):
        self._choose_color(self._appearance[key],
                           lambda color: self._appearance_value(key, color))

    def _choose_color(self, current, callback):
        focus = QtWidgets.QApplication.focusWidget()
        dialog = ColorPickerDialog(current, self)
        self.color_dialog_open = True
        try:
            if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                callback(dialog.selectedColor())
        finally:
            self.color_dialog_open = False
            if focus is not None:
                focus.setFocus(Qt.FocusReason.OtherFocusReason)

    def _appearance_value(self, key, value):
        self._appearance[key] = (QtGui.QColor(value)
                                 if key in ('fill', 'border') else int(value))
        self._refresh_color_buttons()
        self.appearance_requested.emit(self._appearance_copy())

    def _appearance_copy(self):
        return {
            'fill': QtGui.QColor(self._appearance['fill']),
            'border_color': QtGui.QColor(self._appearance['border']),
            'border_width': self._appearance['border_width'],
            'radius': self._appearance['radius'],
        }

    def _toggle_appearance(self):
        if self.parentWidget() is None:
            return
        if self.appearance_popover.isVisible():
            self.appearance_popover.hide()
            return
        self.appearance_popover.adjustSize()
        anchor = self.appearance_button.mapTo(
            self.parentWidget(), QtCore.QPoint(0, 0))
        x = (anchor.x() + self.appearance_button.width()
             - self.appearance_popover.width())
        x = max(6, min(
            x, self.parentWidget().width()
            - self.appearance_popover.width() - 6))
        y = anchor.y() - self.appearance_popover.height() - 6
        if y < 6:
            y = anchor.y() + self.appearance_button.height() + 6
        y = max(6, min(
            y, self.parentWidget().height()
            - self.appearance_popover.height() - 6))
        self.appearance_popover.move(x, y)
        self.appearance_popover.show()
        self.appearance_popover.raise_()

    def reposition_for_rect(self, note_rect):
        """Place above ``note_rect`` in viewport coordinates."""
        viewport = self.parentWidget()
        if viewport is None:
            return
        self.adjustSize()
        rect = QtCore.QRect(note_rect)
        x = rect.center().x() - self.width() // 2
        x = max(6, min(x, viewport.width() - self.width() - 6))
        above = rect.top() - self.height() - 7
        below = rect.bottom() + 7
        y = above if above >= 6 else below
        y = max(6, min(y, viewport.height() - self.height() - 6))
        self.move(x, y)
        if self.appearance_popover.isVisible():
            self._toggle_appearance()
            self._toggle_appearance()

    def hide_popovers(self):
        self.appearance_popover.hide()
