# OpenRef roadmap

## 0.6 — Fast capture and rich notes (in progress)

Images retain native pixel dimensions on paste/import; insertion does not
change the camera. New notes use a readable 18 logical-pixel font, 300-pixel
apparent width, and immediate typing focus. Enter inserts a newline, Escape
commits, and Ctrl/Command+Enter creates the next note below. A contextual
toolbar adds rich formatting and custom note colors, with Markdown paste,
document undo while editing, and full board-level undo after editing.

Native boards use `.openref`. `.bee` imports preserve the original and save
as a new `.openref` copy. Rich content and note appearance must survive copy,
undo, save/reopen, and visual export.

Delegated packets: Terra owns the rich-note model and editing transactions;
Luna owns the isolated contextual toolbar; Luna owns packaging associations
and user documentation. The lead owns file safety, action/view integration,
export, regression review, and release gates. Shared files have one owner.

## 0.7 — Containers and reusable appearance

Ctrl/Command+G frames selected content. Frames have optional names, automatic
drop membership, movable contents, and independently resizable borders.
Start with one frame level. Flat, Soft Shadow, Raised and Inset presets use
up to two customizable shadows. Copy/Paste Appearance uses Ctrl/Command+Alt+C
and Alt+V. Add named appearance presets and Find on Board.

## 0.8 — Drawing cleanup and symbol catalog

Explicit preview/accept for polishing basic shapes or recognizing selected
strokes. Local recognition, reversible replacements, searchable Essentials
and Systems packs, favorites and per-pack/per-symbol enablement. Boards
embed symbol geometry so disabling a pack never removes existing content.

One beta release per completed milestone; Windows and Apple Silicon builds,
corresponding source, checksums, automated checks and native interaction QA
are required. Reusable snippets, viewpoints and attached connectors follow.

## Completed 0.5 interaction pass

This pass groups the 19 user stories into four connected workflows:

1. **Remember context:** persist the last file-dialog folder and chosen pen color
   as application preferences. Existing board files do not need migration.
2. **Create and draw:** reserve `Ctrl+N` (`Command+N` on macOS) for a new text
   box, move New Board to `Ctrl+Shift+N`, scale newly drawn stroke widths by
   the current canvas zoom, and make the hold-to-erase modifier configurable.
3. **Arrange and transform:** selecting content raises it; direct edge and
   corner drags scale proportionally; dragging across the opposite bound
   mirrors it. Layer actions are available in the canvas menu.
4. **Keep spatial context:** toolbar popovers remain anchored to the dock
   during zoom, and Windows fullscreen right-drag restores a centered window
   with the pointer's canvas location preserved.

Release gate: all existing tests, interaction regression tests, lint, macOS
Apple Silicon smoke build, Windows installer smoke build, source archive, and
both published checksums. Use one beta release after the complete pass.

Follow-up product considerations: a more discoverable visual arrange panel,
per-board drawing presets, and broader physical-device QA for high-DPI mice,
trackpads, and multi-monitor fullscreen restoration.
