"""Latency and geometry safeguards for the subtle freehand filter."""

import math

import pytest

from PyQt6 import QtCore, QtGui

from beeref.items import BeePathItem
from beeref.stroke_smoothing import (
    MAX_CORRECTION_PX, local_smoothing_radius, smooth_sample,
)


def test_smoothing_budget_tracks_width_and_zoom_without_exceeding_a_pixel():
    for brush_size in (1, 8, 80, 500):
        for scale in (0.001, 1, 1000):
            radius = local_smoothing_radius(brush_size, scale)
            assert radius * scale <= MAX_CORRECTION_PX + 1e-10
    assert local_smoothing_radius(1, 1) < (
        local_smoothing_radius(8, 1))
    assert math.isclose(local_smoothing_radius(8, 0.01) * 0.01,
                        local_smoothing_radius(8, 1000) * 1000)


def test_sample_correction_is_causal_sideways_and_subpixel():
    before = QtCore.QPointF(0, 0)
    previous = QtCore.QPointF(10, 0)
    raw = QtCore.QPointF(20, 1)
    smoothed = smooth_sample(before, previous, raw, 0.85, 1)

    assert smoothed.x() == raw.x()  # no directional latency
    assert 0 < smoothed.y() < raw.y()
    assert math.hypot(raw.x() - smoothed.x(),
                      raw.y() - smoothed.y()) <= MAX_CORRECTION_PX
    assert before == QtCore.QPointF(0, 0)
    assert previous == QtCore.QPointF(10, 0)


def test_corners_reversals_sparse_samples_and_degenerate_points_untouched():
    before = QtCore.QPointF(0, 0)
    previous = QtCore.QPointF(10, 0)
    for raw in (QtCore.QPointF(10, 10),  # right angle
                QtCore.QPointF(5, 0),    # reversal
                QtCore.QPointF(50, 1),   # input gap / fast movement
                QtCore.QPointF(10, 0)):  # duplicate
        assert smooth_sample(before, previous, raw, 0.85, 1) == raw
    assert smooth_sample(before, before, previous, 0.85, 1) == previous


def test_filter_screen_result_is_same_at_extreme_zooms():
    screen_points = (QtCore.QPointF(0, 0), QtCore.QPointF(10, 0),
                     QtCore.QPointF(20, 1))
    for scale in (0.001, 1, 1000):
        points = [point / scale for point in screen_points]
        radius = local_smoothing_radius(8, scale)
        result = smooth_sample(*points, radius, scale) * scale
        assert math.isclose(result.x(), 20, abs_tol=1e-7)
        assert math.isclose(result.y(), 0.65, abs_tol=1e-7)


def test_new_path_does_not_rewrite_completed_segments(qapp):
    stroke = {
        'tool': 'pen', 'base_size': 8, 'smoothing_radius': 0.85,
        'points': [{'x': 0, 'y': 0}, {'x': 10, 'y': 0},
                   {'x': 20, 'y': 1}],
    }
    item = BeePathItem()
    before = item._stroke_path(stroke)
    prefix = [(before.elementAt(i).x, before.elementAt(i).y,
               before.elementAt(i).type)
              for i in range(before.elementCount())]
    stroke['points'].append({'x': 500, 'y': 300})
    after = item._stroke_path(stroke)
    assert [(after.elementAt(i).x, after.elementAt(i).y,
             after.elementAt(i).type) for i in range(len(prefix))] == prefix
    assert (QtGui.QPainterPath.ElementType.CurveToElement in
            [after.elementAt(i).type
             for i in range(after.elementCount())])


def test_smoothing_geometry_survives_save_data_round_trip(qapp):
    stroke = {
        'tool': 'pen', 'base_size': 8, 'smoothing_radius': 0.85,
        'points': [{'x': 0, 'y': 0}, {'x': 10, 'y': 0},
                   {'x': 20, 'y': 1}],
    }
    item = BeePathItem([stroke])
    reloaded = BeePathItem.create_from_data(
        data=item.get_extra_save_data())

    assert reloaded.strokes == [stroke]
    original_path = item._stroke_path(stroke)
    restored_path = reloaded._stroke_path(reloaded.strokes[0])
    assert original_path == restored_path


def test_deep_zoom_sampling_keeps_subcentimetre_canvas_precision(view):
    view.enter_draw_mode()
    view.scale(1000, 1000)
    view._begin_mark(QtCore.QPointF(0, 0))

    assert not view._append_pen_sample(QtCore.QPointF(0.0007, 0), 1)
    assert view._append_pen_sample(QtCore.QPointF(0.0009, 0), 1)
    assert view.draw_current_stroke['points'][-1]['x'] == 0.0009
    assert math.isclose(view.draw_current_stroke['base_size'] *
                        view.get_scale(), view.draw_brush_size)


def test_pointer_mapping_preserves_fractional_screen_coordinates(view):
    view.scale(1000, 1000)
    viewport_pos = QtCore.QPointF(42.35, 18.65)
    event = QtGui.QMouseEvent(
        QtCore.QEvent.Type.MouseMove, viewport_pos, viewport_pos,
        QtCore.Qt.MouseButton.NoButton, QtCore.Qt.MouseButton.NoButton,
        QtCore.Qt.KeyboardModifier.NoModifier)

    scene_pos = view._scene_pos_from_pointer(event)
    projected = view.viewportTransform().map(scene_pos)

    assert math.isclose(projected.x(), viewport_pos.x(), abs_tol=1e-7)
    assert math.isclose(projected.y(), viewport_pos.y(), abs_tol=1e-7)


def test_scaled_drawing_uses_effective_item_and_camera_scale(view):
    item = BeePathItem()
    item.setScale(2)
    view.scene.addItem(item)
    view.enter_draw_mode(item)
    view._begin_mark(QtCore.QPointF(0, 0))

    stroke = view.draw_current_stroke
    assert math.isclose(stroke['base_size'] * view.get_scale() *
                        item.scale(), view.draw_brush_size)
    assert 'smoothing_radius' in stroke


def test_geometric_tools_are_not_smoothed(view):
    view.enter_draw_mode()
    view.set_draw_tool('line')
    view._begin_mark(QtCore.QPointF(0, 0))
    assert 'smoothing_radius' not in view.draw_current_stroke


def test_release_captures_pointer_endpoint_even_after_sparse_motion(view):
    view.enter_draw_mode()
    view._begin_mark(QtCore.QPointF(0, 0))
    scene_end = QtCore.QPointF(25.25, 5.5)
    viewport_end = view.viewportTransform().map(scene_end)
    release = QtGui.QMouseEvent(
        QtCore.QEvent.Type.MouseButtonRelease,
        viewport_end, viewport_end,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.MouseButton.NoButton,
        QtCore.Qt.KeyboardModifier.NoModifier)

    view.mouseReleaseEvent(release)

    item = next(item for item in view.scene.items()
                if isinstance(item, BeePathItem))
    tip = item.strokes[0]['points'][-1]
    assert math.isclose(tip['x'], scene_end.x(), abs_tol=1e-5)
    assert math.isclose(tip['y'], scene_end.y(), abs_tol=1e-5)


@pytest.mark.parametrize('release_modifiers', (
    QtCore.Qt.KeyboardModifier.ShiftModifier,
    QtCore.Qt.KeyboardModifier.NoModifier,
))
def test_shift_constrained_pen_release_does_not_add_off_axis_tail(
        view, release_modifiers):
    view.enter_draw_mode()
    view._begin_mark(QtCore.QPointF(0, 0))
    move_pos = view.viewportTransform().map(QtCore.QPointF(100, 10))
    move = QtGui.QMouseEvent(
        QtCore.QEvent.Type.MouseMove, move_pos, move_pos,
        QtCore.Qt.MouseButton.NoButton,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.KeyboardModifier.ShiftModifier)
    view.mouseMoveEvent(move)
    assert view._draw_shift_constrained

    release_pos = view.viewportTransform().map(QtCore.QPointF(110, 12))
    release = QtGui.QMouseEvent(
        QtCore.QEvent.Type.MouseButtonRelease,
        release_pos, release_pos,
        QtCore.Qt.MouseButton.LeftButton,
        QtCore.Qt.MouseButton.NoButton,
        release_modifiers)
    view.mouseReleaseEvent(release)

    item = next(item for item in view.scene.items()
                if isinstance(item, BeePathItem))
    points = item.strokes[0]['points']
    assert len(points) == 2
    assert math.isclose(points[0]['y'], points[1]['y'], abs_tol=1e-7)
    assert points[-1]['x'] > 100
    assert not view._draw_shift_constrained
