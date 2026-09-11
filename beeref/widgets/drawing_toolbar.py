"""OpenRef drawing controls that float over the canvas."""

# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright © 2026 Sean Budning and OpenRef contributors.

from PyQt6 import QtCore, QtGui, QtWidgets


Qt = QtCore.Qt


class CanvasToolButton(QtWidgets.QToolButton):
    """Compact icon button drawn with vectors so it stays crisp."""

    def __init__(self, icon_kind, parent=None, tooltip=None):
        super().__init__(parent)
        self.icon_kind = icon_kind
        self.accent = QtGui.QColor('#f5d66f')
        self.stroke_width = 8.0
        self.stroke_style = 'solid'
        self.setCheckable(True)
        self.setFixedSize(30, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            self.setToolTip(tooltip)

    def set_icon_kind(self, icon_kind):
        self.icon_kind = icon_kind
        self.update()

    def set_accent(self, color):
        self.accent = QtGui.QColor(color)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.scale(self.width() / 40, self.height() / 40)
        color = QtGui.QColor('#ececee')
        pen = QtGui.QPen(color, 2.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        kind = self.icon_kind

        if kind == 'pen':
            painter.save()
            painter.translate(20, 19)
            painter.rotate(42)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(QtCore.QRectF(-4, -13, 8, 20), 2, 2)
            painter.setBrush(QtGui.QColor('#aeb2b8'))
            painter.drawRoundedRect(QtCore.QRectF(-4, -14, 8, 4), 1, 1)
            tip = QtGui.QPainterPath()
            tip.moveTo(-4, 7)
            tip.lineTo(4, 7)
            tip.lineTo(0, 14)
            tip.closeSubpath()
            painter.setBrush(self.accent)
            painter.drawPath(tip)
            painter.setBrush(QtGui.QColor('#ececee'))
            painter.drawEllipse(QtCore.QPointF(0, 12.5), 1.2, 1.2)
            painter.restore()
        elif kind == 'line':
            painter.drawLine(QtCore.QPointF(10, 30),
                             QtCore.QPointF(30, 10))
        elif kind == 'rectangle':
            painter.drawRoundedRect(QtCore.QRectF(10, 10, 20, 20), 2, 2)
        elif kind == 'ellipse':
            painter.drawEllipse(QtCore.QRectF(10, 10, 20, 20))
        elif kind == 'eraser':
            painter.save()
            painter.translate(20, 20)
            painter.rotate(-38)
            painter.setPen(QtGui.QPen(color, 2.4))
            painter.setBrush(QtGui.QColor('#2c6972'))
            painter.drawRoundedRect(QtCore.QRectF(-8, -13, 16, 26), 4, 4)
            painter.drawLine(QtCore.QPointF(-8, 3), QtCore.QPointF(8, 3))
            painter.restore()
        elif kind == 'color':
            painter.setPen(QtGui.QPen(color, 2.5))
            painter.setBrush(self.accent)
            painter.drawEllipse(QtCore.QRectF(10, 10, 20, 20))
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 150), 2))
            painter.drawArc(QtCore.QRectF(14, 14, 12, 12), 40 * 16, 90 * 16)
        elif kind == 'width':
            for x, width, height in ((12, 2.0, 12),
                                     (20, 3.0, 18),
                                     (28, 4.0, 24)):
                painter.setPen(QtGui.QPen(
                    color, width, Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap))
                painter.drawLine(QtCore.QPointF(x, 20 - height / 2),
                                 QtCore.QPointF(x, 20 + height / 2))
            self._draw_chevron(painter)
        elif kind == 'style':
            style_pen = QtGui.QPen(color, 2.6)
            style_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            if self.stroke_style == 'dotted':
                style_pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(style_pen)
            painter.drawLine(QtCore.QPointF(9, 20),
                             QtCore.QPointF(28, 20))
            painter.setBrush(color)
            painter.drawEllipse(QtCore.QPointF(9, 20), 2.4, 2.4)
            if self.stroke_style == 'arrow':
                painter.drawLine(QtCore.QPointF(22, 14),
                                 QtCore.QPointF(28, 20))
                painter.drawLine(QtCore.QPointF(22, 26),
                                 QtCore.QPointF(28, 20))
            self._draw_chevron(painter)
        elif kind == 'close':
            painter.setPen(QtGui.QPen(color, 2.2,
                                      cap=Qt.PenCapStyle.RoundCap))
            painter.drawLine(13, 13, 27, 27)
            painter.drawLine(27, 13, 13, 27)

    def _draw_chevron(self, painter):
        painter.setPen(QtGui.QPen(QtGui.QColor('#bfc0c4'), 1.5))
        painter.drawLine(31, 17, 34, 20)
        painter.drawLine(34, 20, 37, 17)


class PopoverFrame(QtWidgets.QFrame):
    """Rounded option card with a small pointer toward its anchor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('drawPopover')
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.Widget)
        self.hide()

    def show_for(self, anchor):
        self.adjustSize()
        parent = self.parentWidget()
        if parent is None:
            self.show()
            return
        anchor_pos = anchor.mapTo(parent, QtCore.QPoint(0, 0))
        x = anchor_pos.x() + (anchor.width() - self.width()) // 2
        x = max(8, min(x, parent.width() - self.width() - 8))
        y = max(8, anchor_pos.y() - self.height() - 6)
        self.move(x, y)
        self.show()
        self.raise_()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        body = QtCore.QRectF(self.rect())
        body.setBottom(body.bottom() - 10)
        path = QtGui.QPainterPath()
        path.addRoundedRect(body, 8, 8)
        center = self.width() / 2
        path.moveTo(center - 10, body.bottom())
        path.lineTo(center, self.height() - 1)
        path.lineTo(center + 10, body.bottom())
        path.closeSubpath()
        painter.fillPath(path, QtGui.QColor('#242527'))
        painter.setPen(QtGui.QPen(QtGui.QColor('#151618'), 1))
        painter.drawPath(path)


class StrokeOptionButton(QtWidgets.QAbstractButton):
    """Visual line width or line style choice."""

    def __init__(self, mode, value, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.value = value
        self.setCheckable(True)
        self.setFixedSize(84, 34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        if self.isChecked() or self.underMouse():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor('#57585a'))
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1),
                                    5, 5)
        color = QtGui.QColor('#f2f2f3')
        if self.mode == 'width':
            width = float(self.value)
            preview = max(1.5, min(10.0, width * 0.7))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(QtCore.QPointF(20, 17),
                                preview / 2, preview / 2)
            pen = QtGui.QPen(color, preview)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(QtCore.QPointF(37, 17),
                             QtCore.QPointF(68, 17))
        else:
            pen = QtGui.QPen(color, 2.8)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            if self.value == 'dotted':
                pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawLine(QtCore.QPointF(16, 17),
                             QtCore.QPointF(68, 17))
            if self.value == 'arrow':
                painter.drawLine(QtCore.QPointF(60, 10),
                                 QtCore.QPointF(68, 17))
                painter.drawLine(QtCore.QPointF(60, 24),
                                 QtCore.QPointF(68, 17))


class StrokePopover(PopoverFrame):

    selected = QtCore.pyqtSignal(object)

    def __init__(self, mode, values, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.buttons = {}
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(7, 7, 7, 16)
        layout.setSpacing(3)
        group = QtWidgets.QButtonGroup(self)
        group.setExclusive(True)
        for value in values:
            button = StrokeOptionButton(mode, value, self)
            button.clicked.connect(
                lambda checked, choice=value: self._choose(choice))
            self.buttons[value] = button
            group.addButton(button)
            layout.addWidget(button)

    def _choose(self, value):
        self.set_value(value)
        self.hide()
        self.selected.emit(value)

    def set_value(self, value):
        if self.mode == 'width':
            choice = min(self.buttons, key=lambda item: abs(item - value))
        else:
            choice = value
        for key, button in self.buttons.items():
            button.setChecked(key == choice)


class ToolPopover(PopoverFrame):

    selected = QtCore.pyqtSignal(str)

    TOOLS = (
        ('pen', 'Pen (D)'),
        ('line', 'Line (L)'),
        ('rectangle', 'Rectangle (R)'),
        ('ellipse', 'Ellipse (C)'),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.buttons = {}
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(7, 7, 7, 16)
        layout.setSpacing(3)
        group = QtWidgets.QButtonGroup(self)
        group.setExclusive(True)
        for tool, tooltip in self.TOOLS:
            button = CanvasToolButton(tool, self, tooltip)
            button.clicked.connect(
                lambda checked, choice=tool: self._choose(choice))
            self.buttons[tool] = button
            group.addButton(button)
            layout.addWidget(button)

    def _choose(self, tool):
        self.set_value(tool)
        self.hide()
        self.selected.emit(tool)

    def set_value(self, tool):
        for key, button in self.buttons.items():
            button.setChecked(key == tool)


class DrawingToolbar(QtWidgets.QFrame):
    """Compact drawing dock with configurable placement."""

    tool_changed = QtCore.pyqtSignal(str)
    style_changed = QtCore.pyqtSignal(str)
    width_changed = QtCore.pyqtSignal(float)
    color_requested = QtCore.pyqtSignal()
    close_requested = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('drawingToolbar')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed,
                           QtWidgets.QSizePolicy.Policy.Fixed)
        self._tool = 'pen'
        self._mark_tool = 'pen'
        self._style = 'solid'
        self._width = 8.0

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(3)

        self.tool_button = CanvasToolButton(
            'pen', self, 'Drawing tools (D, L, R, C)')
        self.tool_button.setChecked(True)
        self.tool_button.clicked.connect(self._show_tools)
        layout.addWidget(self.tool_button)

        self.eraser_button = CanvasToolButton(
            'eraser', self, 'Eraser (E)')
        self.eraser_button.clicked.connect(
            lambda: self._select_tool('eraser'))
        layout.addWidget(self.eraser_button)

        self.color_button = CanvasToolButton(
            'color', self, 'Pen color (Ctrl+T)')
        self.color_button.setCheckable(False)
        self.color_button.clicked.connect(self.color_requested)
        layout.addWidget(self.color_button)

        self.width_button = CanvasToolButton(
            'width', self, 'Line thickness ([ and ])')
        self.width_button.setCheckable(False)
        self.width_button.clicked.connect(self._show_widths)
        layout.addWidget(self.width_button)

        self.style_button = CanvasToolButton(
            'style', self, 'Line style (1, 2, 3)')
        self.style_button.setCheckable(False)
        self.style_button.clicked.connect(self._show_styles)
        layout.addWidget(self.style_button)

        self.close_button = CanvasToolButton(
            'close', self, 'Finish drawing (Esc)')
        self.close_button.setCheckable(False)
        self.close_button.clicked.connect(self.close_requested)
        layout.addWidget(self.close_button)

        popup_parent = parent
        self.tool_popover = ToolPopover(popup_parent)
        self.width_popover = StrokePopover(
            'width', (14.0, 8.0, 3.0), popup_parent)
        self.style_popover = StrokePopover(
            'style', ('solid', 'dotted', 'arrow'), popup_parent)
        self.popovers = (
            self.tool_popover, self.width_popover, self.style_popover)
        self.tool_popover.selected.connect(self._select_tool)
        self.width_popover.selected.connect(self._select_width)
        self.style_popover.selected.connect(self._select_style)
        self.tool_buttons = self.tool_popover.buttons
        self.tool_buttons['eraser'] = self.eraser_button

        self.set_color(QtGui.QColor('#f5d66f'))
        self.set_width(8)
        self.set_style('solid')

    def hide_popovers(self, except_for=None):
        for popover in self.popovers:
            if popover is not except_for:
                popover.hide()

    def _toggle(self, popover, anchor):
        was_visible = popover.isVisible()
        self.hide_popovers()
        if not was_visible:
            popover.show_for(anchor)

    def _show_tools(self):
        self.tool_button.setChecked(self._tool != 'eraser')
        self._toggle(self.tool_popover, self.tool_button)

    def _show_widths(self):
        self._toggle(self.width_popover, self.width_button)

    def _show_styles(self):
        self._toggle(self.style_popover, self.style_button)

    def _select_tool(self, tool):
        self.set_tool(tool)
        self.hide_popovers()
        self.tool_changed.emit(tool)

    def _select_width(self, value):
        self.set_width(value)

    def _select_style(self, value):
        self.set_style(value)
        self.style_changed.emit(value)

    def set_tool(self, tool):
        self._tool = tool
        if tool != 'eraser':
            self._mark_tool = tool
            self.tool_button.set_icon_kind(tool)
        self.tool_button.setChecked(tool != 'eraser')
        self.eraser_button.setChecked(tool == 'eraser')
        self.tool_popover.set_value(
            self._mark_tool if tool == 'eraser' else tool)

    def set_style(self, style):
        self._style = style
        self.style_button.stroke_style = style
        self.style_button.update()
        self.style_popover.set_value(style)

    def set_width(self, width):
        value = max(1.0, min(64.0, float(width)))
        self._width = value
        self.width_button.stroke_width = value
        self.width_button.update()
        self.width_popover.set_value(value)
        self.width_changed.emit(value)

    def set_color(self, color):
        self.color_button.set_accent(color)

    def hideEvent(self, event):
        self.hide_popovers()
        super().hideEvent(event)


class CommandPalette(QtWidgets.QDialog):
    """Searchable launcher for every action already exposed by BeeRef."""

    def __init__(self, parent, action_definitions):
        super().__init__(parent)
        self.setObjectName('commandPalette')
        self.setWindowTitle('Command Palette')
        self.setWindowFlags(Qt.WindowType.Dialog
                            | Qt.WindowType.FramelessWindowHint)
        self.setModal(False)
        self.resize(380, 310)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self.search = QtWidgets.QLineEdit(self)
        self.search.setObjectName('commandSearch')
        self.search.setPlaceholderText('Type a command…')
        self.search.setClearButtonEnabled(True)
        layout.addWidget(self.search)
        self.list = QtWidgets.QListWidget(self)
        self.list.setObjectName('commandList')
        self.list.setUniformItemSizes(True)
        layout.addWidget(self.list)

        self._actions = [
            definition.qaction for definition in action_definitions
            if definition.qaction is not None
            and definition.id != 'command_palette'
        ]
        self.search.textChanged.connect(self._refill)
        self.search.returnPressed.connect(self.run_current)
        self.list.itemActivated.connect(lambda item: self.run_current())
        self._refill('')

    def _refill(self, query):
        query = query.strip().lower()
        self.list.clear()
        for action in self._actions:
            label = action.text().replace('&', '')
            shortcut = action.shortcut().toString()
            haystack = f'{label} {shortcut}'.lower()
            if query and query not in haystack:
                continue
            item = QtWidgets.QListWidgetItem(label)
            if shortcut:
                item.setText(f'{label}    {shortcut}')
            item.setData(Qt.ItemDataRole.UserRole, action)
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)

    def run_current(self):
        item = self.list.currentItem()
        if item is None:
            return
        action = item.data(Qt.ItemDataRole.UserRole)
        self.accept()
        action.trigger()

    def showEvent(self, event):
        super().showEvent(event)
        self.search.clear()
        self.search.setFocus()
