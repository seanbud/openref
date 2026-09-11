from PyQt6 import QtGui, QtWidgets

from beeref.widgets.modern_ui import (
    ColorPickerDialog,
    UnsavedChangesDialog,
    WindowChrome,
)
from beeref.widgets.drawing_toolbar import DrawingToolbar


def test_color_picker_uses_qt_dialog_with_alpha(qtbot, view):
    dialog = ColorPickerDialog(QtGui.QColor(255, 218, 120, 128), view)
    qtbot.addWidget(dialog)

    assert dialog.currentColor().name().upper() == '#FFDA78'
    assert abs(dialog.currentColor().alphaF() - 0.5) < 0.01
    assert dialog.testOption(
        QtWidgets.QColorDialog.ColorDialogOption.ShowAlphaChannel)


def test_color_picker_updates_toolbar_preview_live(qtbot, view):
    dialog = ColorPickerDialog(QtGui.QColor('#FFDA78'), view)
    toolbar = DrawingToolbar(view)
    qtbot.addWidget(dialog)
    qtbot.addWidget(toolbar)
    dialog.color_changed.connect(toolbar.set_color)

    dialog.set_color(QtGui.QColor('#3399FF'))

    assert toolbar.color_button.accent.name().upper() == '#3399FF'


def test_unsaved_dialog_exposes_three_clear_choices(qtbot, view):
    dialog = UnsavedChangesDialog('Unsaved work', view)
    qtbot.addWidget(dialog)

    assert dialog.SAVE == 2
    assert dialog.DISCARD == 1
    assert dialog.CANCEL == 0
    assert dialog.message.text() == 'Unsaved work'
    assert dialog.minimumWidth() == 430


def test_window_chrome_only_reveals_when_enabled(qtbot, view):
    chrome = WindowChrome(view, view.parent, lambda checked: None)
    qtbot.addWidget(chrome)

    chrome.reveal()
    assert chrome.isHidden()

    chrome.set_enabled(True)
    chrome.reveal()
    assert not chrome.isHidden()
