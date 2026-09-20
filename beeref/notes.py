"""Canvas-level capture and contextual rich-note actions."""

# SPDX-License-Identifier: GPL-3.0-or-later

from PyQt6 import QtCore, QtGui, QtWidgets

from beeref import commands
from beeref.actions import actions
from beeref.items import BeeTextItem
from beeref.widgets.note_toolbar import NoteToolbar


class NoteEditingMixin:
    def note_key_action(self, event):
        if self.scene.edit_item is None:
            return None
        sequence = QtGui.QKeySequence(event.keyCombination())
        for action_id in ('note_bold', 'note_italic', 'note_underline',
                          'note_strike', 'paste', 'paste_plain',
                          'paste_markdown', 'undo', 'redo'):
            definition = actions.actions[action_id]
            if any(sequence == QtGui.QKeySequence(shortcut)
                   for shortcut in definition.get_shortcuts()):
                return definition.callback
        if event.key() in (
                QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter,
                QtCore.Qt.Key.Key_Escape, QtCore.Qt.Key.Key_Backspace,
                QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Left,
                QtCore.Qt.Key.Key_Right, QtCore.Qt.Key.Key_Up,
                QtCore.Qt.Key.Key_Down, QtCore.Qt.Key.Key_Home,
                QtCore.Qt.Key.Key_End, QtCore.Qt.Key.Key_PageUp,
                QtCore.Qt.Key.Key_PageDown):
            return 'native'
        for key in (QtGui.QKeySequence.StandardKey.Copy,
                    QtGui.QKeySequence.StandardKey.Cut,
                    QtGui.QKeySequence.StandardKey.SelectAll):
            if event.matches(key):
                return 'native'
        return None

    def init_note_tools(self):
        self.note_toolbar = NoteToolbar(self.viewport())
        self.note_toolbar.format_requested.connect(self.format_note)
        self.note_toolbar.appearance_requested.connect(self.style_note)

    def active_note(self):
        if isinstance(self.scene.edit_item, BeeTextItem):
            return self.scene.edit_item
        selected = self.scene.selectedItems(user_only=True)
        if len(selected) == 1 and isinstance(selected[0], BeeTextItem):
            return selected[0]
        return None

    def refresh_note_tools(self):
        if not hasattr(self, 'note_toolbar'):
            return
        try:
            note = self.active_note()
        except RuntimeError:
            return  # Scene teardown can emit one final selection signal.
        self.actiongroup_set_enabled('active_when_note', note is not None)
        # Ctrl+I means Italic in note context, Insert Images elsewhere.
        actions.actions['insert_images'].qaction.setEnabled(note is None)
        if note is None or self.active_mode == self.DRAW_MODE:
            self.note_toolbar.hide()
            self.note_toolbar.hide_popovers()
            return
        state = note.format_state()
        state['text_width'] = note.textWidth()
        self.note_toolbar.set_state(state)
        self.note_toolbar.set_appearance(note.appearance)
        rect = self.mapFromScene(note.sceneBoundingRect()).boundingRect()
        self.note_toolbar.reposition_for_rect(rect)
        self.note_toolbar.show()
        self.note_toolbar.raise_()

    def on_note_editing_changed(self, item, editing):
        self.refresh_note_tools()

    def _note_dimensions(self):
        try:
            size = int(self.settings.value('Notes/font_size', 18))
            width = int(self.settings.value('Notes/text_width', 300))
        except (TypeError, ValueError):
            size, width = 18, 300
        return max(10, min(size, 72)), max(120, min(width, 800))

    def create_note(self, position=None, text='', mime=None, mode='auto'):
        self.cancel_active_modes()
        size, width = self._note_dimensions()
        item = BeeTextItem(text=text, font_size=size, text_width=width)
        item.setScale(1 / self.get_scale())
        if position is None:
            local = self.viewport().mapFromGlobal(QtGui.QCursor.pos())
            viewport = self.viewport().rect()
            if not viewport.contains(local):
                local = viewport.center()
            x = max(12, min(local.x() + 12, viewport.width() - width - 12))
            y = max(12, min(local.y() + 12, viewport.height() - size * 3 - 12))
            position = self.mapToScene(QtCore.QPoint(x, y))
        item.setPos(position)
        self.undo_stack.push(commands.InsertItems(self.scene, [item]))
        item.enter_edit_mode(select_all=bool(text))
        if mime is not None:
            item.paste_mime(mime, mode=mode)
        self.refresh_note_tools()
        return item

    def create_note_below(self, previous):
        position = previous.mapToScene(QtCore.QPointF(
            0, previous.boundingRect().bottom()))
        position += QtCore.QPointF(0, 14 / self.get_scale())
        item = self.create_note(position=position)
        self.ensureVisible(item, 16, 48)
        return item

    def format_note(self, kind, value=None):
        note = self.active_note()
        if note is None:
            return
        if kind == 'text_width':
            value = max(120, min(int(value), 800))
            self.settings.setValue('Notes/text_width', value)
        if kind == 'font_size':
            self.settings.setValue('Notes/font_size', int(value))
        note.apply_format(kind, value)
        if note.edit_mode:
            note.setFocus(QtCore.Qt.FocusReason.OtherFocusReason)
        self.refresh_note_tools()

    def style_note(self, appearance):
        note = self.active_note()
        if note is not None:
            note.set_appearance(**appearance)
            if note.edit_mode:
                note.setFocus(QtCore.Qt.FocusReason.OtherFocusReason)
            self.refresh_note_tools()

    def on_action_note_bold(self):
        self.format_note('bold')

    def on_action_note_italic(self):
        self.format_note('italic')

    def on_action_note_underline(self):
        self.format_note('underline')

    def on_action_note_strike(self):
        self.format_note('strike')

    def on_action_note_color(self):
        if self.active_note():
            self.note_toolbar._choose_text_color()

    def on_action_note_appearance(self):
        if self.active_note():
            self.note_toolbar._toggle_appearance()

    def paste_note(self, mode='auto'):
        mime = QtWidgets.QApplication.clipboard().mimeData()
        if mime is None or not (mime.hasText() or mime.hasHtml()):
            return
        note = self.scene.edit_item
        if isinstance(note, BeeTextItem):
            note.paste_mime(mime, mode=mode)
        else:
            self.create_note(mime=mime, mode=mode)

    def on_action_paste_plain(self):
        self.paste_note('plain')

    def on_action_paste_markdown(self):
        self.paste_note('markdown')

    def on_action_size_selection_to_view(self):
        self.cancel_active_modes()
        selected = self.scene.selectedItems(user_only=True)
        if not selected:
            return
        rect = self.scene.itemsBoundingRect(items=selected)
        if rect.isEmpty():
            return
        visible = self.mapToScene(self.viewport().rect()).boundingRect()
        factor = min(visible.width() * .8 / rect.width(),
                     visible.height() * .8 / rect.height())
        self.undo_stack.push(commands.ScaleItemsBy(
            selected, factor, rect.center()))
