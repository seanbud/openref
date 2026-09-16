# OpenRef interaction pass

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
