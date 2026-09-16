"""Acceptance coverage for the workflow and canvas interaction pass."""

from unittest.mock import MagicMock, patch

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt

from beeref.actions import actions
from beeref.items import BeePathItem, BeePixmapItem, BeeTextItem


def test_file_dialog_remembers_last_chosen_folder(view, tmp_path):
    folder = tmp_path / 'boards'
    folder.mkdir()
    filename = str(folder / 'reference.bee')
    with patch.object(view, 'do_save') as save:
        with patch.object(QtWidgets.QFileDialog, 'getSaveFileName',
                          return_value=(filename, '')) as dialog:
            view.on_action_save_as()
    assert dialog.call_args.kwargs['directory'] != str(folder)
    assert view._dialog_directory() == str(folder)
    save.assert_called_once_with(filename, create_new=True)


def test_first_dialog_uses_documents_folder(view, tmp_path):
    with patch.object(QtCore.QStandardPaths, 'writableLocation',
                      return_value=str(tmp_path)):
        assert view._dialog_directory() == str(tmp_path)


def test_color_choice_persists_as_next_session_default(view, settings):
    chosen = QtGui.QColor('#7ac5e2')
    with patch('beeref.widgets.modern_ui.ColorPickerDialog') as dialog:
        dialog.return_value.exec.return_value = (
            QtWidgets.QDialog.DialogCode.Accepted)
        dialog.return_value.selectedColor.return_value = chosen
        view.on_action_set_brush_color()
    assert settings.value('Drawing/default_color') == '#ff7ac5e2'

    from beeref.view import BeeGraphicsView
    for action_id in list(actions.actions):
        if action_id.startswith('recent_files_'):
            actions.actions.pop(action_id)
    reopened = BeeGraphicsView(view.app, view.parent)
    assert reopened.draw_brush_color == [122, 197, 226, 255]
    reopened.deleteLater()


def test_new_text_shortcut_exits_draw_mode(qtbot, view):
    assert actions.actions['insert_text'].get_shortcuts() == ['Ctrl+N']
    assert actions.actions['new_scene'].get_shortcuts() == ['Ctrl+Shift+N']
    view.enter_draw_mode()
    qtbot.keyClick(view, Qt.Key.Key_N, Qt.KeyboardModifier.ControlModifier)
    assert view.active_mode != view.DRAW_MODE
    assert any(isinstance(item, BeeTextItem) for item in view.scene.items())


def test_new_board_shortcut_is_distinct_while_drawing(qtbot, view):
    view.enter_draw_mode()
    qtbot.keyClick(view, Qt.Key.Key_N,
                   Qt.KeyboardModifier.ControlModifier
                   | Qt.KeyboardModifier.ShiftModifier)
    assert view.active_mode != view.DRAW_MODE
    assert not any(isinstance(item, BeeTextItem)
                   for item in view.scene.items())


def test_quit_is_directly_in_canvas_context_menu(view):
    assert actions.actions['quit'].qaction in view.context_menu.actions()


def test_stroke_width_is_scaled_to_canvas_zoom(view):
    view.scale(2, 2)
    view.enter_draw_mode()
    view._begin_mark(QtCore.QPointF(20, 20))
    assert view.draw_current_stroke['base_size'] == 4.0


def _image(view):
    image = QtGui.QImage(100, 80, QtGui.QImage.Format.Format_ARGB32)
    item = BeePixmapItem(image)
    view.scene.addItem(item)
    item.setSelected(True)
    return item


def _resize_event(x, y):
    event = MagicMock()
    event.pos.return_value = QtCore.QPointF(x, y)
    event.scenePos.return_value = QtCore.QPointF(x, y)
    event.button.return_value = Qt.MouseButton.LeftButton
    return event


def test_edge_drag_scales_proportionally_and_undoes(view):
    item = _image(view)
    item.mousePressEvent(_resize_event(100, 40))
    assert item.active_mode == item.SCALE_MODE
    item.mouseMoveEvent(_resize_event(150, 40))
    assert round(item.scale(), 2) == 1.5
    item.mouseReleaseEvent(_resize_event(150, 40))
    view.undo_stack.undo()
    assert item.scale() == 1.0


def test_edge_drag_past_opposite_bound_mirrors(view):
    item = _image(view)
    anchor = item.mapToScene(QtCore.QPointF(100, 40))
    item.mousePressEvent(_resize_event(0, 40))
    item.mouseMoveEvent(_resize_event(150, 40))
    assert item.flip() == -1
    assert round(item.scale(), 2) == 0.5
    assert item.mapToScene(QtCore.QPointF(100, 40)) == anchor
    item.mouseReleaseEvent(_resize_event(150, 40))
    view.undo_stack.undo()
    assert item.flip() == 1
    assert item.scale() == 1


def test_thin_stroke_keeps_edge_resize_targets(view):
    stroke = BeePathItem([{
        'tool': 'line', 'style': 'solid',
        'color': [255, 255, 255, 255], 'base_size': 2,
        'points': [{'x': 0, 'y': 0}, {'x': 100, 'y': 0}],
    }])
    stroke._update_bounding_rect()
    view.scene.addItem(stroke)
    stroke.setSelected(True)
    rect = stroke.bounding_rect_unselected()
    top = QtCore.QPointF(rect.center().x(), rect.top())
    left = QtCore.QPointF(rect.left(), rect.center().y())
    assert stroke.get_resize_target(top)[0] == 'edge'
    assert stroke.get_resize_target(left)[0] == 'edge'


def test_top_edge_drag_past_bottom_mirrors_vertically(view):
    item = _image(view)
    item.mousePressEvent(_resize_event(50, 0))
    item.mouseMoveEvent(_resize_event(50, 120))
    assert item.flip() == -1
    assert item.rotation() == 180
    item.mouseReleaseEvent(_resize_event(50, 120))
    view.undo_stack.undo()
    assert item.flip() == 1
    assert item.rotation() == 0


def test_arrange_one_layer_is_undoable(view):
    back, middle, front = [_image(view) for _ in range(3)]
    for item in (back, middle, front):
        item.setSelected(False)
    back.setZValue(1)
    middle.setZValue(2)
    front.setZValue(3)
    middle.setSelected(True)
    view.scene.move_selection_one_layer(forward=True)
    assert middle.zValue() > front.zValue()
    view.undo_stack.undo()
    assert middle.zValue() == 2


def test_drawing_popover_remains_anchored_through_zoom(view):
    view.enter_draw_mode()
    view.draw_toolbar._show_widths()
    popover = view.draw_toolbar.width_popover
    before = popover.pos()
    view.zoom(120, QtCore.QPointF(100, 100))
    assert popover.isVisible()
    assert popover.pos() == before


def test_temporary_eraser_can_be_rebound(qtbot, view, kbsettings):
    kbsettings.set_temporary_eraser_modifier('alt')
    view.enter_draw_mode()
    qtbot.keyPress(view, Qt.Key.Key_Alt)
    assert view.draw_tool == 'eraser'
    qtbot.keyRelease(view, Qt.Key.Key_Alt)
    assert view.draw_tool == 'pen'


def test_drawing_item_can_be_brought_forward(view):
    image = _image(view)
    image.setZValue(2)
    stroke = BeePathItem()
    view.scene.addItem(stroke)
    stroke.setZValue(1)
    stroke.bring_to_front()
    assert stroke.zValue() > image.zValue()


def test_clicking_image_brings_it_above_other_content(qtbot, view):
    behind = _image(view)
    behind.setSelected(False)
    behind.setPos(0, 0)
    behind.setZValue(1)
    front = _image(view)
    front.setSelected(False)
    front.setPos(200, 0)
    front.setZValue(2)
    view.parent.show()
    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton,
                     pos=view.mapFromScene(QtCore.QPointF(50, 40)))
    assert behind.zValue() > front.zValue()


def test_clicking_drawn_stroke_brings_it_to_front(qtbot, view):
    image = _image(view)
    image.setSelected(False)
    image.setPos(200, 0)
    image.setZValue(2)
    stroke = BeePathItem([{
        'tool': 'line', 'style': 'solid',
        'color': [255, 255, 255, 255], 'base_size': 8,
        'points': [{'x': 0, 'y': 0}, {'x': 100, 'y': 0}],
    }])
    stroke._update_bounding_rect()
    view.scene.addItem(stroke)
    stroke.setZValue(1)
    view.parent.show()
    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton,
                     pos=view.mapFromScene(QtCore.QPointF(50, 0)))
    assert stroke.zValue() > image.zValue()


@patch('beeref.main_controls.sys.platform', 'win32')
def test_windows_fullscreen_drag_centers_window_at_pointer(view):
    window = view.parent
    press = MagicMock()
    press.button.return_value = Qt.MouseButton.RightButton
    press.globalPosition.return_value = QtCore.QPointF(300, 300)
    move = MagicMock()
    move.globalPosition.return_value = QtCore.QPointF(350, 350)
    expected_center = QtCore.QPoint(350, 350) - window.rect().center()
    with patch.object(window, 'isFullScreen', return_value=True), \
            patch.object(window, 'showNormal'), \
            patch.object(window, 'move') as move_window, \
            patch.object(view, '_restore_global_canvas_anchor'):
        view.mousePressEventMainControls(press)
        view.mouseMoveEventMainControls(move)
    move_window.assert_any_call(expected_center)
    assert view._fullscreen_anchor[1] == QtCore.QPoint(350, 350)
