"""Compact contextual controls for persistent canvas groups."""

# SPDX-License-Identifier: GPL-3.0-or-later

from PyQt6 import QtCore, QtGui, QtWidgets

from beeref.widgets.note_toolbar import _NoteColorPopover


Qt = QtCore.Qt


class GroupToolbar(QtWidgets.QFrame):
    """Screen-space inspector shown when a group is double-clicked."""

    style_changed = QtCore.pyqtSignal(dict)
    dismissed = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('groupToolbar')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._state = {}

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 4, 5, 4)
        layout.setSpacing(3)

        self.title_edit = QtWidgets.QLineEdit(self)
        self.title_edit.setObjectName('groupTitleEdit')
        self.title_edit.setPlaceholderText('Group title')
        self.title_edit.setFixedWidth(126)
        self.title_edit.textEdited.connect(
            lambda value: self._change(title=value))
        layout.addWidget(self.title_edit)

        self.color_button = QtWidgets.QToolButton(self)
        self.color_button.setText('●')
        self.color_button.setToolTip('Frame color')
        self.color_button.setFixedSize(27, 25)
        self.color_button.clicked.connect(self._show_color)
        layout.addWidget(self.color_button)

        self.style_button = QtWidgets.QToolButton(self)
        self.style_button.setCheckable(True)
        self.style_button.setText('━')
        self.style_button.setToolTip('Solid or dashed frame')
        self.style_button.setFixedSize(29, 25)
        self.style_button.clicked.connect(
            lambda solid: self._change(
                frame_style='solid' if solid else 'dash'))
        layout.addWidget(self.style_button)

        self.fill_button = QtWidgets.QToolButton(self)
        self.fill_button.setCheckable(True)
        self.fill_button.setText('▨')
        self.fill_button.setToolTip('Tint group background')
        self.fill_button.setFixedSize(29, 25)
        self.fill_button.clicked.connect(
            lambda enabled: self._change(fill_enabled=enabled))
        layout.addWidget(self.fill_button)

        close = QtWidgets.QToolButton(self)
        close.setText('×')
        close.setToolTip('Close')
        close.setFixedSize(25, 25)
        close.clicked.connect(self._dismiss)
        layout.addWidget(close)

        self.color_popover = _NoteColorPopover(parent)
        self.color_popover.color_changed.connect(
            lambda color: self._change(frame_color=color.name()))
        self.setStyleSheet('''
            QFrame#groupToolbar {
                background: palette(window); border: 1px solid palette(mid);
                border-radius: 7px;
            }
            QLineEdit#groupTitleEdit {
                border: 0; border-radius: 4px;
                background: rgba(127, 127, 127, 28); padding: 3px 7px;
            }
            QToolButton { border: 0; border-radius: 4px; padding: 0 4px; }
            QToolButton:hover { background: rgba(127, 127, 127, 45); }
            QToolButton:checked { background: rgba(90, 140, 210, 105); }
        ''')
        self.color_popover.setStyleSheet('''
            QFrame#noteColorPopover {
                background: palette(window); border: 1px solid palette(mid);
                border-radius: 7px;
            }
        ''')
        self.hide()

    def set_state(self, state):
        self._state = dict(state)
        self.title_edit.blockSignals(True)
        self.title_edit.setText(self._state.get('title', ''))
        self.title_edit.blockSignals(False)
        self.style_button.setChecked(
            self._state.get('frame_style', 'dash') == 'solid')
        self.fill_button.setChecked(bool(
            self._state.get('fill_enabled', False)))
        color = QtGui.QColor(self._state.get('frame_color', '#8d93a8'))
        self.color_button.setStyleSheet(
            f'QToolButton {{ color: {color.name()}; font-size: 17px; }}')

    def _change(self, **changes):
        self._state.update(changes)
        self.set_state(self._state)
        self.style_changed.emit(dict(self._state))

    def _show_color(self):
        self.color_popover.set_color(
            self._state.get('frame_color', '#8d93a8'), emit=False)
        self.color_popover.show_for(self, getattr(self, '_group_rect', None))

    def show_for(self, group_rect, focus=False):
        viewport = self.parentWidget()
        if viewport is None:
            return
        self.adjustSize()
        self._group_rect = QtCore.QRect(group_rect)
        x = max(6, min(group_rect.left(),
                       viewport.width() - self.width() - 6))
        above = group_rect.top() - self.height() - 7
        y = above if above >= 6 else group_rect.bottom() + 7
        y = max(6, min(y, viewport.height() - self.height() - 6))
        self.move(x, y)
        self.show()
        self.raise_()
        if focus:
            self.title_edit.setFocus(Qt.FocusReason.MouseFocusReason)
            self.title_edit.selectAll()

    def _dismiss(self):
        self.color_popover.hide()
        self.hide()
        self.dismissed.emit()

    def hideEvent(self, event):
        self.color_popover.hide()
        super().hideEvent(event)
