from unittest.mock import patch

from PyQt6 import QtCore

from beeref.items import BeePathItem
from beeref.view import BeeGraphicsView


def test_draw_mode_creates_undoable_item(view):
    view.enter_draw_mode()
    assert view.active_mode == BeeGraphicsView.DRAW_MODE
    assert not view.draw_toolbar.isHidden()

    view._begin_mark(QtCore.QPointF(30, 40))
    view.draw_current_stroke['points'].append({
        'x': 20, 'y': 10, 'pressure': 1.0})
    drawn_item = view.draw_item
    view.exit_draw_mode(commit=True)

    assert drawn_item.scene() is view.scene
    assert len(drawn_item.strokes) == 1
    assert view.undo_stack.count() == 1
    assert view.draw_toolbar.isHidden()
    view.undo_stack.undo()
    assert drawn_item.scene() is None


def test_edit_existing_drawing_is_undoable(view):
    original = [{
        'tool': 'line', 'style': 'solid',
        'color': [255, 255, 255, 255], 'base_size': 5,
        'points': [{'x': 0, 'y': 0}, {'x': 50, 'y': 0}],
    }]
    item = BeePathItem(original)
    item._update_bounding_rect()
    view.scene.addItem(item)

    view.enter_draw_mode(item)
    item.erase_at(QtCore.QPointF(25, 0), 8)
    view.exit_draw_mode(commit=True)
    assert item.scene() is None

    view.undo_stack.undo()
    assert item.scene() is view.scene
    assert item.strokes == original


def test_constrained_shapes_and_lines():
    start = QtCore.QPointF(0, 0)
    square = BeeGraphicsView._constrained_point(
        start, QtCore.QPointF(20, 10), 'rectangle')
    line = BeeGraphicsView._constrained_point(
        start, QtCore.QPointF(20, 3), 'line')

    assert square == QtCore.QPointF(20, 20)
    assert abs(line.y()) < 0.001


def test_draw_mode_keyboard_tool_switch(qtbot, view):
    view.enter_draw_mode()
    qtbot.keyClick(view, QtCore.Qt.Key.Key_R)

    assert view.draw_tool == 'rectangle'
    assert view.draw_toolbar.tool_buttons['rectangle'].isChecked()
    assert view._hud_toast.label.text() == 'Rectangle'
    assert view._hud_toast.shortcut.text() == 'R'


def test_draw_feedback_reuses_toast(view):
    view.enter_draw_mode()
    toast = view._hud_toast
    view.set_draw_width(12)
    view.set_draw_style('dotted')

    assert view._hud_toast is toast
    assert toast.label.text() == 'Dotted stroke'
    assert toast.shortcut.text() == '2'


def test_eraser_gesture_previews_then_commits_as_one_undo(view):
    strokes = [{
        'tool': 'line', 'style': 'solid',
        'color': [255, 255, 255, 255], 'base_size': 5,
        'points': [{'x': 0, 'y': 0}, {'x': 50, 'y': 0}],
    }, {
        'tool': 'line', 'style': 'solid',
        'color': [255, 255, 255, 255], 'base_size': 5,
        'points': [{'x': 0, 'y': 50}, {'x': 50, 'y': 50}],
    }]
    item = BeePathItem(strokes)
    item._update_bounding_rect()
    view.scene.addItem(item)
    view.enter_draw_mode()
    view.set_draw_tool('eraser')

    view._begin_eraser(QtCore.QPointF(20, 0), QtCore.QPointF(20, 0))
    assert len(item.strokes) == 2
    assert item.erase_preview_indexes == {0}

    view._commit_eraser()
    assert len(item.strokes) == 1
    view.undo_stack.undo()
    assert item.strokes == strokes


@patch('beeref.view.sys.platform', 'darwin')
def test_command_temporarily_switches_pen_to_eraser(qtbot, view):
    view.enter_draw_mode()
    view.set_draw_tool('pen')

    qtbot.keyPress(view, QtCore.Qt.Key.Key_Meta)
    assert view.draw_tool == 'eraser'
    qtbot.keyRelease(view, QtCore.Qt.Key.Key_Meta)
    assert view.draw_tool == 'pen'
