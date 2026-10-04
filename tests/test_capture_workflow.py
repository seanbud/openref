"""End-to-end keyboard and document safety coverage for fast capture."""

import hashlib
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt6 import QtCore, QtGui, QtWidgets

from beeref import fileio
from beeref.actions import actions
from beeref.fileio.errors import BeeFileIOError
from beeref.fileio.schema import APPLICATION_ID, USER_VERSION
from beeref.fileio.sql import SQLiteIO
from beeref.items import BeeTextItem


Qt = QtCore.Qt
CTRL = Qt.KeyboardModifier.ControlModifier


def test_new_note_accepts_typing_and_multiline_without_another_click(
        view, qtbot):
    view.scale(2, 2)
    qtbot.keyClick(view, Qt.Key.Key_N, CTRL)
    note = view.scene.edit_item
    assert isinstance(note, BeeTextItem)
    assert note.font().pixelSize() == -1
    assert note.textWidth() == -1
    assert note.scale() == .5
    assert note.toPlainText() == 'Text'
    assert note.textCursor().selectedText() == 'Text'
    qtbot.keyClicks(view, 'First line')
    qtbot.keyClick(view, Qt.Key.Key_Return)
    qtbot.keyClicks(view, 'Second line')
    assert note.toPlainText() == 'First line\nSecond line'
    qtbot.keyClick(view, Qt.Key.Key_Escape)
    assert view.scene.edit_item is None
    assert note.toPlainText() == 'First line\nSecond line'


def test_editor_shortcuts_format_and_undo_without_exiting(view, qtbot):
    note = view.create_note()
    qtbot.keyClicks(view, 'Hello')
    qtbot.keyClick(view, Qt.Key.Key_A, CTRL)
    qtbot.keyClick(view, Qt.Key.Key_B, CTRL)
    assert (note.textCursor().charFormat().fontWeight()
            >= QtGui.QFont.Weight.Bold)
    qtbot.keyClick(view, Qt.Key.Key_Z, CTRL)
    assert note.edit_mode
    assert note.toPlainText() == 'Hello'
    assert (note.textCursor().charFormat().fontWeight()
            < QtGui.QFont.Weight.Bold)


def test_next_note_commits_and_aligns_below(view, qtbot):
    first = view.create_note()
    qtbot.keyClicks(view, 'First')
    qtbot.keyClick(view, Qt.Key.Key_Return, CTRL)
    second = view.scene.edit_item
    assert second is not first
    assert first.toPlainText() == 'First'
    assert not first.edit_mode
    assert second.pos().x() == first.pos().x()
    assert second.pos().y() > first.sceneBoundingRect().bottom()
    qtbot.keyClicks(view, 'Second')
    assert second.toPlainText() == 'Second'


def test_toolbar_preserves_selected_text(view, qtbot):
    note = view.create_note(text='Style me')
    assert note.textCursor().selectedText() == 'Style me'
    view.parent.show()
    point = view.mapFromScene(note.sceneBoundingRect().center())
    qtbot.mouseMove(view.viewport(), point)
    view.refresh_note_tools()
    assert view.note_toolbar.isVisible()
    qtbot.mouseClick(view.note_toolbar.format_buttons['underline'],
                     Qt.MouseButton.LeftButton)
    assert note.edit_mode
    assert note.textCursor().selectedText() == 'Style me'
    assert note.textCursor().charFormat().fontUnderline()
    qtbot.keyClicks(view, 'Replacement')
    assert note.toPlainText() == 'Replacement'


def test_toolbar_grace_period_keeps_hover_controls_reachable(view, qtbot):
    note = view.create_note(text='Reachable controls')
    view.parent.show()
    qtbot.mouseMove(
        view.viewport(), view.mapFromScene(note.sceneBoundingRect().center()))
    view.refresh_note_tools()
    assert view.note_toolbar.isVisible()

    # Leaving the text starts a short bridge rather than destroying the bar.
    qtbot.mouseMove(view.viewport(), QtCore.QPoint(
        view.viewport().width() - 3, view.viewport().height() - 3))
    view.refresh_note_tools()
    assert view.note_toolbar.isVisible()

    # Re-entering the bar during that bridge cancels the pending hide.
    qtbot.mouseMove(view.note_toolbar, view.note_toolbar.rect().center())
    qtbot.wait(600)
    assert view.note_toolbar.isVisible()


def test_editor_paste_formats_markdown_and_plain_paste_stays_literal(
        view, qtbot):
    note = view.create_note()
    mime = QtCore.QMimeData()
    mime.setText('**bold**')
    clipboard = MagicMock()
    clipboard.mimeData.return_value = mime
    with patch.object(QtWidgets.QApplication, 'clipboard',
                      return_value=clipboard):
        qtbot.keyClick(view, Qt.Key.Key_V, CTRL)
        assert note.toPlainText() == 'bold'
        qtbot.keyClick(view, Qt.Key.Key_V,
                       CTRL | Qt.KeyboardModifier.ShiftModifier)
    assert '**bold**' in note.toPlainText()


def test_format_shortcuts_can_be_rebound(view, qtbot):
    definition = actions.actions['note_underline']
    definition.set_shortcuts(['Ctrl+Alt+U'])
    note = view.create_note(text='Underlined')
    qtbot.keyClick(view, Qt.Key.Key_U,
                   CTRL | Qt.KeyboardModifier.AltModifier)
    assert note.textCursor().charFormat().fontUnderline()


def test_pasted_image_keeps_source_pixels_with_bounded_initial_size(
        view, qtbot):
    image = QtGui.QImage(1920, 1080, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtGui.QColor('white'))
    clipboard = MagicMock()
    clipboard.image.return_value = image
    clipboard.mimeData.return_value = QtCore.QMimeData()
    view.scale(.5, .5)
    transform = view.transform()
    with patch.object(QtWidgets.QApplication, 'clipboard',
                      return_value=clipboard):
        view.on_action_paste()
    qtbot.wait(1)
    item = view.scene.selectedItems(user_only=True)[0]
    assert item.width == 1920 and item.height == 1080
    displayed_width = item.width * item.scale() * abs(view.get_scale())
    displayed_height = item.height * item.scale() * abs(view.get_scale())
    assert item.scale() < 1
    assert displayed_width <= view.viewport().width() * .72 + 1
    assert displayed_height <= view.viewport().height() * .72 + 1
    assert view.transform() == transform


def test_note_round_trip_preserves_leading_spaces_and_tabs(qapp):
    text = '  indented\n\tTabbed\n    nested'
    note = BeeTextItem(text)

    restored = BeeTextItem(**note.text_state())

    assert restored.toPlainText() == text


def test_note_controls_hide_without_a_text_selection(view, qtbot):
    note = view.create_note(text='Anchored')
    view.parent.show()
    # Move somewhere outside the note before inspecting hover-only controls.
    cursor = note.textCursor()
    cursor.clearSelection()
    note.setTextCursor(cursor)
    view.refresh_note_tools()
    assert not view.note_toolbar.isVisible()
    cursor = note.textCursor()
    cursor.clearSelection()
    note.setTextCursor(cursor)
    view.refresh_note_tools()
    assert not view.note_toolbar.isVisible()
    view.zoom(120, QtCore.QPointF(100, 100))
    view.pan(QtCore.QPoint(100, 40))
    assert note.edit_mode


def test_legacy_import_preserves_original_bytes(view, tmp_path):
    source = Path(__file__).parent / 'assets' / 'test1item.bee'
    original = tmp_path / 'legacy.bee'
    original.write_bytes(source.read_bytes())
    before = hashlib.sha256(original.read_bytes()).hexdigest()
    fileio.load_bee(str(original), view.scene)
    view.scene.add_queued_items()
    output = tmp_path / 'converted.openref'
    fileio.save_bee(str(output), view.scene, create_new=True)
    assert hashlib.sha256(original.read_bytes()).hexdigest() == before
    with sqlite3.connect(output) as connection:
        assert connection.execute('PRAGMA application_id').fetchone()[0] \
            == APPLICATION_ID
        assert connection.execute('PRAGMA user_version').fetchone()[0] \
            == USER_VERSION


def test_future_board_is_rejected_without_rewriting(view, tmp_path):
    filename = tmp_path / 'future.openref'
    with sqlite3.connect(filename) as connection:
        connection.execute(f'PRAGMA application_id={APPLICATION_ID}')
        connection.execute(f'PRAGMA user_version={USER_VERSION + 1}')
    original = filename.read_bytes()
    with pytest.raises(BeeFileIOError) as error:
        SQLiteIO(str(filename), view.scene, readonly=True).read()
    assert 'newer version' in error.value.msg
    with pytest.raises(BeeFileIOError, match='newer version'):
        fileio.save_bee(str(filename), view.scene)
    assert filename.read_bytes() == original


def test_failed_save_as_preserves_destination_and_save_ids(view, tmp_path):
    note = BeeTextItem('Keep me')
    view.scene.addItem(note)
    note.save_id = 17
    filename = tmp_path / 'existing.openref'
    filename.write_bytes(b'original destination')
    with patch.object(SQLiteIO, 'write_data',
                      side_effect=ValueError('failed')):
        with pytest.raises(BeeFileIOError, match='failed'):
            fileio.save_bee(str(filename), view.scene, create_new=True)
    assert filename.read_bytes() == b'original destination'
    assert note.save_id == 17


def test_legacy_first_save_requests_native_copy(view):
    view.filename = '/tmp/reference.bee'
    with patch.object(view, 'on_action_save_as') as save_as:
        view.on_action_save()
    save_as.assert_called_once()
