# OpenRef product direction

OpenRef's current interaction model is the product baseline. The near-term
roadmap favors speed, reliability, and refinement of the existing board,
drawing, notes, grouping, themes, and appearance tools over adding a second
design system or speculative recognition features.

## 0.7 — Performance and scale

The 0.7 milestone makes dense visual boards remain responsive without
removing capabilities or changing their final appearance. Its primary stress
case is a board with many overlapping freehand strokes, large zoom ranges,
and one or more shared drop shadows.

The implementation priorities are:

1. Reuse immutable drawing paths and selection outlines instead of rebuilding
   them for every repaint and hit test.
2. Suspend expensive decorative shadow passes only while the user is actively
   zooming, panning, dragging, or drawing a selection box, then restore the
   exact saved appearance when the interaction settles.
3. Keep canvas bounds and group bookkeeping off pointer-move hot paths where
   possible, while preserving persistent used-space behavior.
4. Add regression tests for cache invalidation, overlapping interactions, and
   final visual restoration. Avoid timing assertions that vary by hardware.

Release gates are the complete automated suite, Python 3.9–3.12 CI, Windows
installer smoke tests, Apple Silicon application smoke tests, source archive,
and published checksums. Performance work must preserve save compatibility,
undo/redo, native-resolution image insertion, zoom anchoring, selection,
eraser behavior, shadows at rest, and screen-pinned controls.

## Current product principles

- Fast capture: paste imagery at native pixel dimensions and create editable
  notes immediately from the keyboard.
- Direct manipulation: selection, arrangement, grouping, drawing, resizing,
  and canvas navigation remain reversible and spatially predictable.
- Quiet polish: contextual controls stay out of the way, themes remain
  optional, and transient feedback never interrupts work.
- Open files: `.openref` remains the native format and `.bee` imports remain
  non-destructive.

Future feature work will be evaluated against real workflows after 0.7. The
previous planned appearance-container and automatic symbol-recognition
milestones are intentionally retired.
