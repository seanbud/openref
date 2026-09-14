from PyQt6 import QtCore, QtGui

from beeref.widgets.modern_ui import (
    ColorPickerDialog,
    UnsavedChangesDialog,
    WindowChrome,
)
from beeref.widgets.drawing_toolbar import DrawingToolbar


def test_color_picker_is_compact_custom_dialog_with_alpha(qtbot, view):
    dialog = ColorPickerDialog(QtGui.QColor(255, 218, 120, 128), view)
    qtbot.addWidget(dialog)

    assert dialog.currentColor().name().upper() == '#FFDA78'
    assert abs(dialog.currentColor().alphaF() - 0.5) < 0.01
    assert dialog.objectName() == 'colorDialog'
    assert dialog.field.minimumWidth() <= dialog.width()
    assert dialog.testAttribute(
        QtCore.Qt.WidgetAttribute.WA_StyledBackground)
    assert not dialog.testAttribute(
        QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)


def test_color_picker_updates_toolbar_preview_live(qtbot, view):
    dialog = ColorPickerDialog(QtGui.QColor('#FFDA78'), view)
    toolbar = DrawingToolbar(view)
    qtbot.addWidget(dialog)
    qtbot.addWidget(toolbar)
    dialog.color_changed.connect(toolbar.set_color)

    dialog.set_color(QtGui.QColor('#3399FF'))

    assert toolbar.color_button.accent.name().upper() == '#3399FF'


def test_color_picker_remembers_applied_colors(qtbot, view, settings):
    dialog = ColorPickerDialog(QtGui.QColor('#3399FF'), view)
    qtbot.addWidget(dialog)
    dialog.accept()

    reopened = ColorPickerDialog(QtGui.QColor('#FFFFFF'), view)
    qtbot.addWidget(reopened)

    assert reopened.recent_colors[0] == '#FF3399FF'


def test_color_picker_can_pin_and_unpin_current_color(qtbot, view, settings):
    dialog = ColorPickerDialog(QtGui.QColor('#F58AA8'), view)
    qtbot.addWidget(dialog)

    dialog.pin_button.setChecked(True)
    assert dialog.pinned_colors == ['#FFF58AA8']
    assert dialog.pin_button.text() == '★'

    reopened = ColorPickerDialog(QtGui.QColor('#F58AA8'), view)
    qtbot.addWidget(reopened)
    assert reopened.pin_button.isChecked()
    reopened.pin_button.setChecked(False)
    assert reopened.pinned_colors == []


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
