from PyQt6 import QtGui

from beeref.actions import actions
from beeref.widgets.drawing_toolbar import CommandPalette, DrawingToolbar


def test_drawing_toolbar_updates_controls(qtbot):
    toolbar = DrawingToolbar()
    qtbot.addWidget(toolbar)

    toolbar.set_tool('ellipse')
    toolbar.set_style('dotted')
    toolbar.set_width(14)
    toolbar.set_color(QtGui.QColor(10, 20, 30, 200))

    assert toolbar.tool_buttons['ellipse'].isChecked()
    assert toolbar.style_button.stroke_style == 'dotted'
    assert toolbar._width == 14
    assert toolbar.color_button.accent == QtGui.QColor(10, 20, 30, 200)
    assert toolbar.sizeHint().width() <= 210


def test_drawing_toolbar_popovers_select_visual_options(qtbot):
    toolbar = DrawingToolbar()
    qtbot.addWidget(toolbar)

    with qtbot.waitSignal(toolbar.width_changed) as signal:
        toolbar.width_popover._choose(14.0)
    assert signal.args == [14.0]

    with qtbot.waitSignal(toolbar.style_changed) as signal:
        toolbar.style_popover._choose('arrow')
    assert signal.args == ['arrow']
    assert toolbar.style_button.stroke_style == 'arrow'


def test_command_palette_filters_actions(qtbot, view):
    palette = CommandPalette(view, actions.actions.values())
    qtbot.addWidget(palette)
    palette._refill('draw')

    assert palette.list.count() == 1
    assert 'Draw' in palette.list.item(0).text()
