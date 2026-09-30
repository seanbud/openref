from PyQt6 import QtCore, QtGui, QtWidgets

from beeref.widgets.note_toolbar import NoteToolbar


def test_note_toolbar_has_only_quiet_format_and_color_controls(qtbot):
    viewport = QtWidgets.QWidget()
    viewport.resize(500, 300)
    qtbot.addWidget(viewport)
    toolbar = NoteToolbar(viewport)
    qtbot.addWidget(toolbar)

    toolbar.set_state({'bold': True, 'italic': False, 'color': '#ff3366'})
    assert toolbar.buttons['bold'].isChecked()
    assert toolbar.text_color_button is not None
    assert toolbar.text_color_button.text() == '●'
    assert not hasattr(toolbar, 'font_size_combo')
    assert not hasattr(toolbar, 'appearance_button')

    with qtbot.waitSignal(toolbar.format_requested) as signal:
        toolbar.buttons['underline'].click()
    assert signal.args == ['underline', True]


def test_note_color_popover_is_compact_and_applies_swatch_live(qtbot):
    viewport = QtWidgets.QWidget()
    viewport.resize(500, 300)
    viewport.show()
    qtbot.addWidget(viewport)
    toolbar = NoteToolbar(viewport)
    qtbot.addWidget(toolbar)
    note_rect = QtCore.QRect(185, 220, 90, 30)
    toolbar.reposition_for_rect(note_rect)
    toolbar.show()

    qtbot.mouseClick(toolbar.text_color_button,
                     QtCore.Qt.MouseButton.LeftButton)
    popover = toolbar.color_popover
    assert popover.isVisible()
    assert popover.width() <= 194
    assert popover.width() > popover.height()
    assert not popover.geometry().intersects(note_rect)
    assert popover.swatch_layout.count() == 12
    swatch = popover.swatch_layout.itemAt(1).widget()
    with qtbot.waitSignal(toolbar.format_requested) as signal:
        qtbot.mouseClick(swatch, QtCore.Qt.MouseButton.LeftButton)
    assert signal.args[0] == 'color'
    assert isinstance(signal.args[1], QtGui.QColor)


def test_note_toolbar_controls_do_not_take_focus(qtbot):
    viewport = QtWidgets.QWidget()
    qtbot.addWidget(viewport)
    toolbar = NoteToolbar(viewport)
    qtbot.addWidget(toolbar)
    assert toolbar.focusPolicy() == QtCore.Qt.FocusPolicy.NoFocus
    assert all(button.focusPolicy() == QtCore.Qt.FocusPolicy.NoFocus
               for button in toolbar.buttons.values())
    assert (toolbar.text_color_button.focusPolicy()
            == QtCore.Qt.FocusPolicy.NoFocus)
