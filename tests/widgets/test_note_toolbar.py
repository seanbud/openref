from PyQt6 import QtCore, QtWidgets

from beeref.widgets.note_toolbar import NoteToolbar


def test_note_toolbar_state_and_format_signals(qtbot):
    viewport = QtWidgets.QWidget()
    viewport.resize(500, 300)
    qtbot.addWidget(viewport)
    toolbar = NoteToolbar(viewport)
    qtbot.addWidget(toolbar)

    toolbar.set_state({'bold': True, 'italic': False, 'font_size': 24,
                       'color': '#ff3366'})
    assert toolbar.buttons['bold'].isChecked()
    assert toolbar.font_size_combo.currentText() == '24'
    assert toolbar.text_color_button is not None

    with qtbot.waitSignal(toolbar.format_requested) as signal:
        toolbar.buttons['underline'].click()
    assert signal.args == ['underline', True]


def test_note_toolbar_appearance_and_position_are_clamped(qtbot):
    viewport = QtWidgets.QWidget()
    viewport.resize(300, 180)
    qtbot.addWidget(viewport)
    toolbar = NoteToolbar(viewport)
    qtbot.addWidget(toolbar)
    toolbar.set_appearance({'fill': '#123456', 'border_width': 4,
                            'corner_radius': 20})
    assert toolbar.border_width_spin.value() == 4
    assert toolbar.corner_radius_spin.value() == 20

    toolbar.reposition_for_rect(QtCore.QRect(0, 0, 25, 25))
    assert toolbar.x() >= 6
    assert toolbar.y() >= 6
    assert toolbar.geometry().right() < viewport.width()
    assert toolbar.geometry().bottom() < viewport.height()

    with qtbot.waitSignal(toolbar.appearance_requested) as signal:
        toolbar.border_width_spin.setValue(5)
    assert signal.args[0]['border_width'] == 5


def test_note_toolbar_controls_do_not_take_focus(qtbot):
    viewport = QtWidgets.QWidget()
    qtbot.addWidget(viewport)
    toolbar = NoteToolbar(viewport)
    qtbot.addWidget(toolbar)
    assert toolbar.focusPolicy() == QtCore.Qt.FocusPolicy.NoFocus
    assert all(button.focusPolicy() == QtCore.Qt.FocusPolicy.NoFocus
               for button in toolbar.buttons.values())
    assert (toolbar.font_size_combo.focusPolicy()
            == QtCore.Qt.FocusPolicy.NoFocus)
