"""Native, offscreen coverage for the OpenRef rich-note data contract."""

from beeref.items import BeeTextItem


def test_rich_note_state_round_trips(qapp):
    note = BeeTextItem(text='Hello', html='<p><b>Hello</b></p>',
                       font_size=18, text_width=300,
                       appearance={'fill': '#112233', 'radius': 12})

    data = note.get_extra_save_data()
    assert data['text'] == 'Hello'
    assert 'font-weight:700' in data['html']
    assert data['font_size'] == 18
    assert data['text_width'] == 300
    assert data['appearance']['fill'] == '#112233'
    assert BeeTextItem.create_from_data(data=data).toPlainText() == 'Hello'


def test_copy_preserves_rich_state_and_transforms(qapp):
    note = BeeTextItem(html='<p><i>italic</i></p>', font_size=18,
                       text_width=300)
    note.setPos(20, 10)
    note.setRotation(24)
    note.setScale(1.5)
    note.do_flip()

    clone = note.create_copy()
    assert clone.get_extra_save_data() == note.get_extra_save_data()
    assert clone.pos() == note.pos()
    assert clone.rotation() == note.rotation()
    assert clone.scale() == note.scale()
    assert clone.flip() == -1


def test_format_and_markdown_paste_are_rich_and_safe(qapp):
    note = BeeTextItem(text='', font_size=18, text_width=300)
    note.enter_edit_mode()
    note.paste_mime({'text': '# Heading\n\n**bold**'}, mode='markdown')
    assert 'Heading' in note.toPlainText()
    assert 'bold' in note.toPlainText()
    assert 'font-weight:700' in note.document().toHtml()

    note.paste_mime({'html': '<img src="https://invalid.example/x.png">'
                     '<u>safe</u>'})
    assert 'safe' in note.toPlainText()
    assert 'invalid.example' not in note.document().toHtml()


def test_markdown_round_trip_keeps_heading_list_code_and_link_label(qapp):
    note = BeeTextItem(text='', font_size=18, text_width=300)
    note.enter_edit_mode()
    note.paste_mime({'text': '# Heading\n\n- first\n- second\n\n'
                     '`code` [read me](https://example.invalid)'},
                    mode='markdown')
    restored = BeeTextItem.create_from_data(data=note.get_extra_save_data())
    html = restored.document().toHtml()
    assert all(word in restored.toPlainText()
               for word in ('Heading', 'first', 'second', 'code', 'read me'))
    assert '<ul' in html
    assert 'monospace' in html
    assert 'example.invalid' not in html


def test_edit_session_is_one_undo_and_empty_note_is_removed(view):
    note = BeeTextItem(text='', font_size=18, text_width=300)
    view.scene.addItem(note)
    note.enter_edit_mode()
    note.setPlainText('one session')
    note.exit_edit_mode()
    assert view.scene.undo_stack.count() == 1

    view.scene.undo_stack.undo()
    assert note.toPlainText() == ''
    view.scene.undo_stack.redo()
    assert note.toPlainText() == 'one session'

    note.enter_edit_mode()
    note.setPlainText('')
    note.exit_edit_mode()
    assert note.scene() is None
    view.scene.undo_stack.undo()
    assert note.scene() is view.scene
    assert note.toPlainText() == 'one session'


def test_appearance_and_width_are_undoable_outside_editor(view):
    note = BeeTextItem(text='note', font_size=18, text_width=300)
    view.scene.addItem(note)
    note.set_appearance(fill='#224466', border_width=2)
    assert note.appearance['fill'] == '#224466'
    view.scene.undo_stack.undo()
    assert note.appearance['fill'] == '#28000000'

    note.apply_format('text_width', 420)
    assert note.text_width == 420
    view.scene.undo_stack.undo()
    assert note.text_width == 300


def test_non_edit_formatting_selects_all_and_is_one_board_undo(view):
    note = BeeTextItem(text='all of this', font_size=18, text_width=300)
    view.scene.addItem(note)

    note.apply_format('bold', True)
    assert 'font-weight:700' in note.document().toHtml()
    assert view.scene.undo_stack.count() == 1
    # An explicit value is idempotent, rather than toggling back off.
    note.apply_format('bold', True)
    assert view.scene.undo_stack.count() == 1
    view.scene.undo_stack.undo()
    assert 'font-weight:700' not in note.document().toHtml()


def test_non_edit_font_size_is_undoable(view):
    note = BeeTextItem(text='sized', font_size=18, text_width=300)
    view.scene.addItem(note)
    note.apply_format('font_size', 24)
    assert note.font_size == 24
    assert note.format_state()['font_size'] == 24
    view.scene.undo_stack.undo()
    assert note.font_size == 18


def test_edit_controls_keep_selection_and_native_undo(view):
    note = BeeTextItem(text='keep this selection', font_size=18,
                       text_width=300)
    view.scene.addItem(note)
    note.enter_edit_mode(select_all=True)
    cursor = note.textCursor()
    start, end = cursor.selectionStart(), cursor.selectionEnd()
    note.set_appearance(radius=14)
    assert (note.textCursor().selectionStart(),
            note.textCursor().selectionEnd()) == (start, end)

    note.apply_format('text_width', 420)
    assert (note.textCursor().selectionStart(),
            note.textCursor().selectionEnd()) == (start, end)
    cursor = note.textCursor()
    cursor.insertText('changed')
    assert note.document().isUndoAvailable()
    note.set_appearance(fill='#336699')
    note.document().undo()
    assert 'changed' not in note.toPlainText()


def test_placeholder_is_not_note_content(qapp):
    note = BeeTextItem(text='', font_size=18, text_width=300)
    note.enter_edit_mode()
    assert note.toPlainText() == ''
    assert note.get_extra_save_data()['text'] == ''
