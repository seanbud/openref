"""Acceptance coverage for the workflow and canvas interaction pass."""

from unittest.mock import MagicMock, patch

import pytest

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt

from beeref.actions import actions
from beeref.items import BeeGroupItem, BeePathItem, BeePixmapItem, BeeTextItem


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


def test_deep_zoom_pressure_does_not_inflate_stroke_width(view):
    view.scale(1000, 1000)
    view.enter_draw_mode()
    view._begin_mark(QtCore.QPointF(20, 20))
    stroke = view.draw_current_stroke
    stroke['points'][0]['pressure'] = .1
    painter = MagicMock()

    view.draw_item._paint_stroke(painter, stroke)

    pen = painter.setPen.call_args_list[-1].args[0]
    assert pen.widthF() == pytest.approx(.0008)


def test_completed_freehand_geometry_does_not_move_with_new_sample():
    stroke = {
        'tool': 'pen', 'style': 'solid',
        'color': [255, 255, 255, 255], 'base_size': 2,
        'points': [
            {'x': 0, 'y': 0}, {'x': 10, 'y': 4}, {'x': 20, 'y': 0},
        ],
    }
    item = BeePathItem([stroke])
    before = item._stroke_path(stroke)
    before_elements = [
        (before.elementAt(index).x, before.elementAt(index).y)
        for index in range(before.elementCount())
    ]

    stroke['points'].append({'x': 400, 'y': 300})
    after = item._stroke_path(stroke)
    after_prefix = [
        (after.elementAt(index).x, after.elementAt(index).y)
        for index in range(len(before_elements))
    ]

    assert after_prefix == before_elements


@pytest.mark.parametrize('modifier', [
    Qt.KeyboardModifier.ControlModifier,
    Qt.KeyboardModifier.ShiftModifier,
])
def test_modifier_click_adds_drawing_to_selection(view, qtbot, modifier):
    center = view.mapToScene(view.viewport().rect().center())
    drawings = []
    for y in (-30, 30):
        drawing = BeePathItem([{
            'tool': 'line', 'style': 'solid',
            'color': [255, 255, 255, 255], 'base_size': 8,
            'points': [{'x': -30, 'y': 0}, {'x': 30, 'y': 0}],
        }])
        drawing._update_bounding_rect()
        drawing.setPos(center + QtCore.QPointF(0, y))
        view.scene.addItem(drawing)
        drawings.append(drawing)
    drawings[0].setSelected(True)

    click_position = view.mapFromScene(drawings[1].mapToScene(
        QtCore.QPointF(0, 0)))
    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton,
                     modifier, click_position)

    assert set(view.scene.selectedItems(user_only=True)) == set(drawings)


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
    event.modifiers.return_value = Qt.KeyboardModifier.NoModifier
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


def test_zoom_temporarily_hides_shadow_composites_and_restores_them(view):
    note = BeeTextItem('Zoom me')
    view.scene.addItem(note)
    note.setSelected(True)
    view.on_action_toggle_shadow()
    composite = next(iter(view.scene._shadow_composites.values()))
    assert composite.isVisible()

    view.zoom(80, QtCore.QPointF(100, 100))
    assert view._zoom_interaction_active is True
    assert composite.isVisible() is False

    view._finish_zoom_interaction()
    assert view._zoom_interaction_active is False
    assert composite.isVisible() is True


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
    view.undo_stack.undo()
    assert behind.zValue() == 1
    view.undo_stack.redo()
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
    view.undo_stack.undo()
    assert stroke.zValue() == 1


def test_click_to_front_keeps_multiselection_order_and_is_one_undo(view):
    back, middle, front = [_image(view) for _ in range(3)]
    for item, z_value in zip((back, middle, front), (1, 2, 3)):
        item.setZValue(z_value)
        item.setSelected(False)
    back.setSelected(True)
    middle.setSelected(True)

    assert view.scene.bring_items_to_front([back, middle])
    assert front.zValue() < back.zValue() < middle.zValue()
    view.undo_stack.undo()
    assert (back.zValue(), middle.zValue(), front.zValue()) == (1, 2, 3)
    view.undo_stack.redo()
    assert front.zValue() < back.zValue() < middle.zValue()


def test_send_to_back_shortcut_has_deterministic_undo_and_redo(qtbot, view):
    back, selected, front = [_image(view) for _ in range(3)]
    back.setZValue(1)
    selected.setZValue(2)
    front.setZValue(3)
    back.setSelected(False)
    front.setSelected(False)
    selected.setSelected(True)

    view.on_action_lower_to_bottom()
    assert selected.zValue() < back.zValue() < front.zValue()
    view.undo_stack.undo()
    assert (back.zValue(), selected.zValue(), front.zValue()) == (1, 2, 3)
    view.undo_stack.redo()
    assert selected.zValue() < back.zValue() < front.zValue()


def test_group_shortcut_creates_movable_persistent_frame(qtbot, view):
    left, right = _image(view), _image(view)
    right.setPos(180, 20)
    left.setSelected(True)
    right.setSelected(True)

    qtbot.keyClick(view, Qt.Key.Key_G, Qt.KeyboardModifier.ControlModifier)

    groups = list(view.scene.items_by_type('group'))
    assert len(groups) == 1
    group = groups[0]
    assert isinstance(group, BeeGroupItem)
    assert set(group.members()) == {left, right}
    assert group.zValue() < min(left.zValue(), right.zValue())
    original_left = QtCore.QPointF(left.pos())
    group.setPos(group.pos() + QtCore.QPointF(20, 12))
    assert left.pos() == original_left + QtCore.QPointF(20, 12)
    assert group.get_extra_save_data()['group_id'] == left.group_id

    view.undo_stack.undo()
    assert not list(view.scene.items_by_type('group'))
    assert left.group_id is None and right.group_id is None
    view.undo_stack.redo()
    assert len(list(view.scene.items_by_type('group'))) == 1


def test_drop_shadow_toggles_for_text_and_drawing_with_undo(view):
    note = BeeTextItem('Depth')
    stroke = BeePathItem([{
        'tool': 'line', 'style': 'solid',
        'color': [255, 255, 255, 255], 'base_size': 2,
        'points': [{'x': 0, 'y': 0}, {'x': 40, 'y': 0}],
    }])
    stroke._update_bounding_rect()
    view.scene.addItem(note)
    view.scene.addItem(stroke)
    note.setSelected(True)
    stroke.setSelected(True)

    view.on_action_toggle_shadow()
    assert note.shadow['enabled'] is True
    assert stroke.shadow['enabled'] is True
    assert note.shadow['group_id'] == stroke.shadow['group_id']
    composites = view.scene._shadow_composites
    assert len(composites) == 1
    composite = next(iter(composites.values()))
    assert set(composite.proxies) == {note, stroke}
    assert composite.graphicsEffect() is not None
    # The live items draw their selection affordances themselves; only the
    # clean proxy layer receives an effect.
    assert note.graphicsEffect() is None
    assert stroke.graphicsEffect() is None

    view.undo_stack.undo()
    assert note.shadow['enabled'] is False
    assert stroke.shadow['enabled'] is False
    view.undo_stack.redo()
    assert note.shadow['enabled'] is True
    assert stroke.shadow['enabled'] is True


def test_drop_shadow_can_be_toggled_off_immediately(view):
    note = BeeTextItem('Depth')
    view.scene.addItem(note)
    note.setSelected(True)

    assert view.scene.toggle_shadows() is True
    assert len(view.scene._shadow_composites) == 1
    assert view.scene.toggle_shadows() is False

    assert note.shadow['enabled'] is False
    assert view.scene._shadow_composites == {}


def test_shadow_proxy_refreshes_while_note_text_changes(view):
    note = BeeTextItem('Before')
    view.scene.addItem(note)
    note.setSelected(True)
    view.scene.toggle_shadows()
    composite = next(iter(view.scene._shadow_composites.values()))
    proxy = composite.proxies[note]

    with patch.object(proxy, 'update') as update:
        note.setPlainText('After')

    update.assert_called()


def test_multiple_drawings_share_a_single_shadow_composite(view):
    drawings = []
    for y in (0, 20):
        item = BeePathItem([{
            'tool': 'line', 'style': 'solid',
            'color': [255, 255, 255, 255], 'base_size': 4,
            'points': [{'x': 0, 'y': y}, {'x': 80, 'y': y}],
        }])
        item._update_bounding_rect()
        view.scene.addItem(item)
        item.setSelected(True)
        drawings.append(item)

    view.on_action_toggle_shadow()

    assert len(view.scene._shadow_composites) == 1
    composite = next(iter(view.scene._shadow_composites.values()))
    assert set(composite.proxies) == set(drawings)
    assert all(item.graphicsEffect() is None for item in drawings)


def test_shadow_proxy_follows_only_its_moved_source(view):
    note = BeeTextItem('Move me')
    view.scene.addItem(note)
    note.setSelected(True)
    view.on_action_toggle_shadow()
    composite = next(iter(view.scene._shadow_composites.values()))
    proxy = composite.proxies[note]

    note.setPos(QtCore.QPointF(42, 24))

    assert proxy.pos() == note.pos()


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
