# This file is part of BeeRef.
#
# BeeRef is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BeeRef is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BeeRef.  If not, see <https://www.gnu.org/licenses/>.

from importlib.resources import files as rsc_files
import logging
from pathlib import Path
import sys

from PyQt6 import QtCore, QtWidgets, QtGui
from PyQt6.QtCore import Qt

from beeref import constants, commands
from beeref.config import logfile_name
from beeref.widgets import (  # noqa: F401
    controls,
    settings,
    welcome_overlay,
    color_gamut,
    drawing_toolbar,
    modern_ui,
)


logger = logging.getLogger(__name__)


class BeeProgressDialog(QtWidgets.QProgressDialog):

    def __init__(self, label, worker, maximum=0, parent=None):
        super().__init__(label, 'Cancel', 0, maximum, parent=parent)
        logger.debug('Initialised progress bar')
        self.setMinimumDuration(0)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setAutoReset(False)
        self.setAutoClose(False)
        worker.begin_processing.connect(self.on_begin_processing)
        worker.progress.connect(self.on_progress)
        worker.finished.connect(self.on_finished)
        worker.user_input_required.connect(self.on_finished)
        self.canceled.connect(worker.on_canceled)

    def on_progress(self, value):
        logger.debug(f'Progress dialog: {value}')
        self.setValue(value)

    def on_begin_processing(self, value):
        logger.debug(f'Beginn progress dialog: {value}')
        self.setMaximum(value)

    def on_finished(self, *args, **kwargs):
        logger.debug('Finished progress dialog')
        self.setValue(self.maximum())
        self.reset()
        self.hide()
        QtCore.QTimer.singleShot(100, self.deleteLater)


class HelpDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(f'{constants.APPNAME} Help')

        tabs = QtWidgets.QTabWidget()

        # Controls
        controls_txt = rsc_files(
            'beeref.documentation').joinpath('controls.html').read_text()
        controls_label = QtWidgets.QLabel(controls_txt)
        controls_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(controls_label)
        tabs.addTab(scroll, '&Controls')

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(tabs)

        # Bottom row of buttons
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.show()


def _bundled_legal_text(filename, fallback):
    """Read a legal file from source or a frozen application bundle."""

    roots = []
    if getattr(sys, 'frozen', False):
        frozen_root = getattr(sys, '_MEIPASS', Path(sys.executable).parent)
        roots.append(Path(frozen_root))
    roots.append(Path(__file__).resolve().parents[2])
    for root in roots:
        path = root / filename
        if path.is_file():
            return path.read_text(encoding='utf-8')
    return fallback


class AboutDialog(QtWidgets.QDialog):
    """Display project identity, GPL terms, attribution, and source access."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(f'About {constants.APPNAME}')
        self.resize(540, 430)

        tabs = QtWidgets.QTabWidget(self)
        about = QtWidgets.QLabel(
            f'<h2>{constants.APPNAME} {constants.VERSION}</h2>'
            f'<p>{constants.APPNAME_FULL}</p>'
            '<p>A free and open-source reference canvas based on BeeRef.</p>'
            f'<p>{constants.COPYRIGHT}</p>'
            '<p>Independent software; not affiliated with or endorsed by '
            'other reference-board products.</p>'
            '<p>Official binaries use Qt through PyQt6 and are distributed '
            'under GNU GPL version 3 only. You may use, study, modify, and '
            'redistribute them under that license. This software comes with '
            '<b>no warranty</b>.</p>'
            f'<p><a href="{constants.WEBSITE}">Project website and source'
            '</a></p>')
        about.setWordWrap(True)
        about.setOpenExternalLinks(True)
        about.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction)
        tabs.addTab(about, 'About')

        license_text = _bundled_legal_text(
            'LICENSE',
            'GNU General Public License version 3 or later.\n\n'
            f'See {constants.WEBSITE}/blob/main/LICENSE for the full text.')
        license_view = QtWidgets.QPlainTextEdit(license_text, self)
        license_view.setReadOnly(True)
        tabs.addTab(license_view, 'License')

        notices = _bundled_legal_text(
            'NOTICE',
            'OpenRef is based on BeeRef by Rebecca Breu and contributors.')
        source = _bundled_legal_text(
            'SOURCE_CODE.txt',
            f'Complete corresponding source: {constants.WEBSITE}')
        source_view = QtWidgets.QPlainTextEdit(
            f'{source.rstrip()}\n\n{notices.rstrip()}\n', self)
        source_view.setReadOnly(True)
        tabs.addTab(source_view, 'Source & credits')

        third_party = _bundled_legal_text(
            'THIRD_PARTY_NOTICES.md',
            'Third-party notices are available with official builds and at '
            f'{constants.WEBSITE}/blob/main/THIRD_PARTY_NOTICES.md')
        third_party_view = QtWidgets.QPlainTextEdit(third_party, self)
        third_party_view.setReadOnly(True)
        tabs.addTab(third_party_view, 'Third-party licenses')

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close, parent=self)
        buttons.rejected.connect(self.reject)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)
        self.show()


class DebugLogDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(f'{constants.APPNAME} Debug Log')
        with open(logfile_name()) as f:
            self.log_txt = f.read()

        self.log = QtWidgets.QPlainTextEdit(self.log_txt)
        self.log.setReadOnly(True)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        self.copy_button = QtWidgets.QPushButton('Co&py To Clipboard')
        self.copy_button.released.connect(self.copy_to_clipboard)
        buttons.addButton(
            self.copy_button, QtWidgets.QDialogButtonBox.ButtonRole.ActionRole)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        name_widget = QtWidgets.QLabel(logfile_name())
        name_widget.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(name_widget)
        layout.addWidget(self.log)
        layout.addWidget(buttons)
        self.show()

    def copy_to_clipboard(self):
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(self.log_txt)


class SceneToPixmapExporterDialog(QtWidgets.QDialog):
    MIN_SIZE = 10
    MAX_SIZE = 100000

    def __init__(self, parent, default_size):
        super().__init__(parent)
        self.default_size = default_size
        if (self.default_size.width() > self.MAX_SIZE
                or self.default_size.width() >= self.MAX_SIZE):
            self.default_size.scale(
                self.MAX_SIZE, self.MAX_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio)

        self.ignore_change = False
        self.setWindowTitle('Export Scene to Image')
        self.setWindowModality(Qt.WindowModality.WindowModal)
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        width_label = QtWidgets.QLabel('Width:')
        layout.addWidget(width_label, 0, 0)
        self.width_input = QtWidgets.QSpinBox()
        self.width_input.setRange(self.MIN_SIZE, self.MAX_SIZE)
        self.width_input.setValue(default_size.width())
        self.width_input.valueChanged.connect(self.on_width_changed)
        layout.addWidget(self.width_input, 0, 1)

        height_label = QtWidgets.QLabel('Height:')
        layout.addWidget(height_label, 1, 0)
        self.height_input = QtWidgets.QSpinBox()
        self.height_input.setMinimum(10)
        self.height_input.setRange(self.MIN_SIZE, self.MAX_SIZE)
        self.height_input.setValue(default_size.height())
        self.height_input.valueChanged.connect(self.on_height_changed)
        layout.addWidget(self.height_input, 1, 1)

        # Bottom row of buttons
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons, 3, 1)

    def on_width_changed(self, width):
        if not self.ignore_change:
            self.ignore_change = True
            new = self.default_size.scaled(
                width, self.MAX_SIZE, Qt.AspectRatioMode.KeepAspectRatio)
            self.height_input.setValue(new.height())
            self.ignore_change = False

    def on_height_changed(self, height):
        if not self.ignore_change:
            self.ignore_change = True
            new = self.default_size.scaled(
                self.MAX_SIZE, height, Qt.AspectRatioMode.KeepAspectRatio)
            self.width_input.setValue(new.width())
            self.ignore_change = False

    def value(self):
        return QtCore.QSize(self.width_input.value(),
                            self.height_input.value())


class ChangeOpacityDialog(QtWidgets.QDialog):

    def __init__(self, parent, images, undo_stack):
        super().__init__(parent)
        self.undo_stack = undo_stack
        self.images = images
        self.command = commands.ChangeOpacity(images, opacity=1)

        value = int(images[0].opacity() * 100) if images else 100

        self.setWindowTitle('Change Opacity:')
        self.setWindowModality(Qt.WindowModality.WindowModal)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.label = QtWidgets.QLabel('Opacity:')
        layout.addWidget(self.label)

        self.input = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        self.input.valueChanged.connect(self.on_value_changed)
        self.input.setRange(0, 100)
        self.input.setValue(value)
        layout.addWidget(self.input)

        # Bottom row of buttons
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.show()

    def on_value_changed(self, value):
        self.label.setText(f'Opacity: {value}%')
        self.command.opacity = value / 100
        self.command.redo()

    def accept(self):
        if self.images:
            logger.debug(f'Setting opacity to {self.command.opacity}')
            self.command.ignore_first_redo = True
            self.undo_stack.push(self.command)
        return super().accept()

    def reject(self):
        self.command.undo()
        return super().reject()


class BeeNotification(QtWidgets.QFrame):
    """A reusable, non-blocking action confirmation HUD.

    Messages hold long enough to read and then ease away. Calling ``present``
    while a toast is visible replaces it in place, which keeps repeated
    shortcuts (brush sizing, toggles, undo) feeling immediate instead of
    producing a stack of notifications.
    """

    HOLD_MS = 1450
    FADE_MS = 320
    BOTTOM_MARGIN = 38

    def __init__(self, parent, text, icon='✓', shortcut=None,
                 duration=None):
        super().__init__(parent)
        self.host = parent
        self.setObjectName('BeeNotification')
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(11, 8, 10, 8)
        layout.setSpacing(7)

        self.icon = QtWidgets.QLabel(self)
        self.icon.setObjectName('notificationIcon')
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon.setFixedSize(18, 18)
        layout.addWidget(self.icon)

        self.label = QtWidgets.QLabel(self)
        self.label.setObjectName('notificationText')
        layout.addWidget(self.label)

        self.shortcut = QtWidgets.QLabel(self)
        self.shortcut.setObjectName('notificationShortcut')
        layout.addWidget(self.shortcut)

        self.opacity_effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.fade = QtCore.QPropertyAnimation(
            self.opacity_effect, b'opacity', self)
        self.fade.setDuration(self.FADE_MS)
        self.fade.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self.fade.finished.connect(self.hide)

        self.hold_timer = QtCore.QTimer(self)
        self.hold_timer.setSingleShot(True)
        self.hold_timer.timeout.connect(self.start_fade)
        self.present(text, icon=icon, shortcut=shortcut, duration=duration)

    def present(self, text, icon='✓', shortcut=None, duration=None):
        """Show or replace the current message and restart its lifetime."""

        self.hold_timer.stop()
        self.fade.stop()
        self.opacity_effect.setOpacity(1.0)
        self.icon.setText(icon or '✓')
        self.label.setText(text)
        self.shortcut.setText(shortcut or '')
        self.shortcut.setVisible(bool(shortcut))
        self.adjustSize()
        self.reposition()
        self.show()
        self.raise_()
        self.hold_timer.start(duration or self.HOLD_MS)

    def reposition(self):
        self.adjustSize()
        x = max(12, (self.host.width() - self.width()) // 2)
        y = max(12, self.host.height() - self.height() - self.BOTTOM_MARGIN)
        self.move(x, y)

    def start_fade(self):
        self.fade.stop()
        self.fade.setStartValue(self.opacity_effect.opacity())
        self.fade.setEndValue(0.0)
        self.fade.start()


class SampleColorWidget(QtWidgets.QWidget):

    OFFSET = 10  # Offset from mouse pointer
    SIZE = 50
    NONE_COLOR = QtGui.QColor(0, 0, 0, 0)

    def __init__(self, parent, pos, color):
        super().__init__(parent)
        self.color = color
        self.set_pos(pos)
        self.show()

    def set_pos(self, pos):
        self.setGeometry(int(pos.x() + self.OFFSET),
                         int(pos.y() + self.OFFSET),
                         self.SIZE, self.SIZE)

    def paintEvent(self, event):
        color = self.color if self.color else self.NONE_COLOR
        painter = QtGui.QPainter(self)
        painter.setBrush(QtGui.QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, 0, self.SIZE, self.SIZE)

    def update(self, pos, color):
        self.set_pos(pos)
        self.color = color
        self.repaint()


class ExportImagesFileExistsDialog(QtWidgets.QDialog):

    def __init__(self, parent, filename):
        super().__init__(parent)
        self.setWindowTitle('File exists')

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        label = QtWidgets.QLabel(
            f'File already exists:\n{filename}')
        layout.addWidget(label)

        choices = (('skip', 'Skip this file'),
                   ('skip_all', 'Skip all existing files'),
                   ('overwrite', 'Overwrite this file'),
                   ('overwrite_all', 'Overwrite all existing files'))

        self.radio_buttons = {}
        for (value, label) in choices:
            btn = QtWidgets.QRadioButton(label)
            self.radio_buttons[value] = btn
            layout.addWidget(btn)
        self.radio_buttons['skip'].setChecked(True)

        # Bottom row of buttons
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def get_answer(self):
        for value, btn in self.radio_buttons.items():
            if btn.isChecked():
                return value
