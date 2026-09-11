0.4.0 - Unreleased
==================

Added
-----

* Canvas drawing tools: pressure-aware pen, line, rectangle, ellipse and
  stroke eraser, with solid, dotted and arrow styles.
* Floating drawing toolbar and efficient drawing shortcuts.
* Double-click editing for saved drawing items and full undo/redo support for
  drawing sessions.
* Searchable command palette (Ctrl + Shift + P).
* Drawing persistence in ``.bee`` files and inclusion in raster/SVG exports.
* Bottom-center action feedback HUD with shortcut hints, message replacement,
  timed hold, and eased fade-out animation.
* Compact drawing dock with anchored tool, thickness, and line-style popovers.
* Purpose-built pen color picker, hover-revealed frameless window controls,
  and a three-way save/discard/cancel warning.
* Live pen-color preview in the drawing dock while the color picker is open.
* Seven original interface themes: OpenRef Midnight, Graphite, Sakura, Deep
  Ocean, Forest, Warm Paper, and Soft Light, with configurable drawing toolbar
  placement in any canvas corner.
* In-app license, corresponding-source, and contributor-attribution screens.
* A fully custom compact HSV/alpha color studio with live drawing-dock preview.
* Persistent used-canvas bounds: content expands the brighter workspace while
  Fit Canvas explicitly trims it back to current content.
* Reversible eraser previews with a soft cursor trail and single-step undo.

Changed
-------

* Renamed the application and public fork to OpenRef, with a distinct desktop
  icon and updated application/package metadata.
* Refreshed the dark theme and redesigned the empty board around the OpenRef
  wordmark and a small set of useful shortcuts.
* The compact frameless canvas and hover-revealed window controls are now the
  default; a native title bar remains available from the View menu.
* Reduced canvas UI scale and redrew drawing/chrome icons around OpenRef's own
  visual language, with one-pixel black window and dock outlines.
* Batched SQLite item writes and accelerated color sampling on large images.
* Library imports no longer consume unrelated host-process command-line flags.
* Added shortcuts for always-on-top, fullscreen, focusing the canvas or
  selection, and changing item depth.
* Added GPLv3, exact-source, and attribution material to every installer.
* Freehand marks now use jitter-filtered, smooth interpolated curves at every
  zoom level.
* Mouse-wheel zoom is effectively unbounded and remains centered beneath the
  pointer; fullscreen right-drag pans the canvas.
* Windowed right-drag moves an unlocked window, with a persistent lock toggle.
* Holding Command while drawing with the pen temporarily activates the eraser
  on macOS and restores the pen on release.
* Right-drag moves windowed canvases on macOS and Windows. In fullscreen,
  macOS right-drag pans while Windows restores and moves the window. Middle
  drag consistently pans the canvas on both platforms.
* Every completed stroke is an independent selectable and erasable object;
  older multi-stroke drawings remain compatible.
* Right-click menus open on release and are suppressed after a meaningful
  window drag. Fullscreen transitions preserve the canvas's screen anchor.
* Native macOS pinch gestures zoom around the gesture position, and Delete or
  Backspace removes selected objects.

Fixed
-----

* The custom color studio now paints an opaque frame and can be moved by
  dragging its header.
* macOS Command-to-erase recognizes Qt's platform-specific modifier mapping.
* Used canvas space is always repainted as one enclosing rectangle, and the
  eraser preview now has a short, tapered fade.

The drawing foundation was contributed by Cinderflame-Linear in PR #150.
Performance work draws from PR #154 by Feihei, and command-line parsing from
PR #117 by DarkDefender.


0.3.4-dev (unreleased)
======================

Added
-----

* Added a setting to change the default memory limit for individual
  images. If a big image won't load, increase this limit. This
  setting can be overridden by Qt's default environment variable
  QT_IMAGEIO_MAXALLOC
* Display error messages when images can't be loaded from bee files
* Added option to export all images from scene (File -> Export Images)
* Added a confirmation dialog when attempting to close unsaved files.
  The confirmation dialog can be disalbed in:
  Settings -> Miscellaneous -> Confirm when closing an unsaved file
* Add option to arrange by filename (Arrange -> Square (by filename))
* Added a setting to choose the default arrange method on importing
  images in batch.
  (Settings -> Settings -> Images & Items -> Default Arrange Method).
* Added the ability to open image files from command line. If the
  first command line arg is a bee file, it will be opened and all
  further files will be ignored, as previously. If the first argument
  isn't a bee file, all files will be treated as images and inserted
  as if opened with "Insert -> Images".

Fixed
-----

* Fixed a case where adding/importing an image would hang when the image
  contained unsupported exif data (#111)
* Fixed a hang when saving an open bee file that had been removed
  since being opened
* Shortcuts now only trigger once when holding down the key
  combination to avoid inconstistend program states and potential
  crashes (by DarkDefender)
* Fixed a crash when pressing the crop shortcut while dragging an image
  (by DarkDefender)


Changed
-------

* Arrange Horiszontal/Vertical now also sort by filename instead of
  the previous seemingly random behaviour


0.3.3 - 2024-05-05
==================

Added
-----

* Moving the window from within BeeRef now changes to a diffent cursor from
  the default arrow cursor.
* Added a color sampler which can copy colors from images to the
  clipboard in hex format (Images -> Sample Color)
* Added notification when attempting to paste from an empty or
  unusable clipboard
* Added panning via scrollwheel:
  * Scroll wheel + Shift + Ctrl: pan vertically
  * Scroll wheel + Shift: pan horizontally
* Make mouse and mouse wheel controls configurable
  (Settings -> Keyboard & Mouse)


Fixed
-----

* Fixed a crash when pressing the keyboard shortcut for New Scene
  while in the process of doing a rubberband selection.
* The checkmark of the menu entry Images -> Grayscale is now updating
  correctly depending on the selected images.
* Removed black line under marching ants outline of crop mode, which
  would scale with the image and get potentially very thick.
* Fixed a crash when importing images with unsupported exif orientation info
* Fixed threading issue when importing images (causing potential
  hangs/weird behaviour)
* Fixed an intermittent crash when invoking New Scene
* Fixed bee files hanging on to disk space of deleted images (issue #99)
* Fixed Drag @ Drop from pinterest feed (by Randommist)
* Fixed pasted items being inserted behind existing items



0.3.2 - 2024-01-21
==================

Added
-----

* For arranging, a gap between images can now be configured in the
  settings.
* The opacity of images can be changed (Images -> Change Opacity).
* Images can be set to display as grayscale (Images -> Grayscale).
* The scene can now also be exported as SVG
* Keyboard shortcuts can now be edited from within BeeRef (Settings ->
  Keyboard Shortcuts). The KeyboardSettings.ini file will now only
  store values which are changed from the default, since it's no longer
  needed as a reference.
* Settings dialog now displays icons to indicate changes from default
  values


Fixed
-----

* Scene Export: Fix output image size and margins when scene had been
  scaled or moved.
* Scene Export: Selecting filename without file extension now
  automatically appends the extension from the selected filter instead
  of resulting in a confusing error message.
* The exemption from antialias/smoothing for images displayed at large
  zoom now also works on images that are flipped horizontally


Changed
-------

* Improved performance of Select All/Deselect All



0.3.1 - 2023-12-10
==================

Added
-----

* Images can now be stored JPG or PNG inside the bee file. By default,
  small images and images with an alpha channel will be stored as PNG,
  the rest as JPG. In the newly created settings dialog, this
  behaviour can be changed to always use PNG (the former behaviour) or
  always JPG. To apply this behaviour to already saved images in
  existing bee files, you can save them as new files.
* Enabled antialiasing/smoothing. Images that are being displayed at a
  large zoom factor are exempt to make sure that icons, pixel sprites
  etc can be viewed correctly.
* A scene can now be exported to a single image (File -> Export Scene...)
* Alternative way to move the BeeRef window without the title bar:
  View -> Move Window (or press "M")


Changed
-------

* Editing of text items will now be undoable after leaving edit mode
* Empty text items will be deleted after leaving edit mode
* Text edit mode can now be aborted with Escape
* "Save as" will now open pre-select the folder of the currently opened file
* "Save" and "Save as" are now inactive when the scene is empty


Fixed
-----

* Fixed a bug where the binary data of deleted images would still hang
  around in the bee file.
* The shortcut to move the BeeRef window (Ctrl + Alt + Drag)
  now works on an empty scene
* Crash when copying an item from a bee file, opening a new scene and
  pasting the image into it.


0.3.0 - 2023-11-23
==================

Added
-----

* Image cropping (Go to "Transform -> Crop", or press Shift + C)
* Show list of recent files on welcome screen
* Keyboard shortcuts can now be configured via a settings file.
  Go to "Settings -> Open Settings Folder" and edit KeyboardSettings.ini
* Remember window geometry when closing (by David Andrs)

Fixed
-----

* Various typos (by luzpaz)
* Ensure that small items always have an area in the middle for
  moving/editing that doesn't trigger transform actions
* Ensure that the first click to select an item doesn't immediately trigger
  transform actions


0.2.0 - 2021-09-06
==================

Note that bee files from version 0.2.0 won't open in BeeRef 0.1.x.

Added
-----

* You can now add plain text notes and paste text from the clipboard
* You can now open bee files from finder on MacOS (by David Andrs)
* Dragging bee files onto an empty scene will now open them
* Adding the first image(s) to a new scene centers the view

Changed
-------

* Make debug log file less verbose
* The program is now bundled as a single executable file (issue #4)

Fixed
-----

* Hovering over the scale handles of very narrow items now displays
  correct cursor orientation
* Fix a rare crash while displaying selection handles


0.1.1 - 2021-07-18
==================

Changed
-------

* Flipping an image now happens on mouse press instead of mouse release
* About dialog points to new website beeref.org
* Menus and dialogs now have a dark style to match the optics of the canvas

Fixed
-----

* Double click to zoom an item and double-clicking again should now always
  correctly go back to the previous position
* The outline of the rubberband selection now stays the same size
  regardless of zoom


0.1.0 - 2021-07-10
==================

First release!
