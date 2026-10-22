"""Small, causal corrections for newly captured freehand strokes.

The ink tip is never predicted and completed points are never revisited. All
limits are expressed in *screen* pixels, then converted to item coordinates
at capture time so zooming an existing board cannot reshape its marks.
"""

import math

from PyQt6 import QtCore


SAMPLE_SPACING_PX = 0.8
MAX_CORRECTION_PX = 0.85
MAX_SAMPLE_JUMP_PX = 24.0
MIN_FORWARD_COSINE = math.cos(math.radians(55))


def local_smoothing_radius(brush_size_px, item_to_screen_scale):
    """Allow at most a subpixel correction, proportional to pen width."""

    scale = max(abs(float(item_to_screen_scale)), 1e-9)
    return min(MAX_CORRECTION_PX, max(0.0, brush_size_px) * 0.12) / scale


def smooth_sample(before, previous, raw, radius, item_to_screen_scale):
    """Reduce tiny sideways jitter without lagging or rounding a corner.

    Only the incoming point changes. Directional progress is left untouched;
    reversals, tight turns, and sparse/high-speed samples bypass the filter.
    """

    direction = previous - before
    movement = raw - previous
    prior_length = math.hypot(direction.x(), direction.y())
    move_length = math.hypot(movement.x(), movement.y())
    if prior_length < 1e-12 or move_length < 1e-12:
        return QtCore.QPointF(raw)
    if move_length * abs(item_to_screen_scale) > MAX_SAMPLE_JUMP_PX:
        return QtCore.QPointF(raw)
    cosine = (direction.x() * movement.x() +
              direction.y() * movement.y()) / (prior_length * move_length)
    if cosine < MIN_FORWARD_COSINE:
        return QtCore.QPointF(raw)

    normal_x = -direction.y() / prior_length
    normal_y = direction.x() / prior_length
    sideways = movement.x() * normal_x + movement.y() * normal_y
    correction = math.copysign(min(abs(sideways) * 0.35, radius), sideways)
    return QtCore.QPointF(raw.x() - normal_x * correction,
                          raw.y() - normal_y * correction)


def causal_curve_controls(before, start, end, radius):
    """Bound a cubic's tangent so a distant sample cannot pull the line."""

    previous = start - before
    segment = end - start
    previous_length = math.hypot(previous.x(), previous.y())
    segment_length = math.hypot(segment.x(), segment.y())
    if previous_length < 1e-12 or segment_length < 1e-12:
        return QtCore.QPointF(start), QtCore.QPointF(end)
    cosine = (previous.x() * segment.x() +
              previous.y() * segment.y()) / (
                  previous_length * segment_length)
    # A sharp corner stays a corner; gentle changes receive slight rounding.
    turn_weight = max(0.0, min(1.0, (
        cosine - MIN_FORWARD_COSINE) / (1.0 - MIN_FORWARD_COSINE)))
    start_length = min(previous_length, segment_length) * 0.25
    start_length = min(start_length, radius) * turn_weight
    end_length = min(segment_length * 0.25, radius)
    control_1 = start + previous / previous_length * start_length
    control_2 = end - segment / segment_length * end_length
    return control_1, control_2
