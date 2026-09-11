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

import logging
import os.path

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt

from beeref.main_controls import MainControlsMixin


logger = logging.getLogger(__name__)


class RecentFilesModel(QtCore.QAbstractListModel):
    """An entry in the 'Recent Files' list."""

    def __init__(self, files):
        super().__init__()
        self.files = files

    def rowCount(self, parent):
        return len(self.files)

    def data(self, index, role):
        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            return os.path.basename(self.files[index.row()])
        if role == QtCore.Qt.ItemDataRole.FontRole:
            font = QtGui.QFont()
            font.setUnderline(True)
            return font


class RecentFilesView(QtWidgets.QListView):

    def __init__(self, parent, view, files=None):
        super().__init__(parent)
        self.view = view
        self.files = files or []
        self.clicked.connect(self.on_clicked)
        self.setModel(RecentFilesModel(self.files))
        self.setMouseTracking(True)

    def on_clicked(self, index):
        self.view.open_from_file(self.files[index.row()])

    def update_files(self, files):
        self.files = files
        self.model().files = files
        self.reset()

    def sizeHint(self):
        size = QtCore.QSize()
        if not self.files:
            return size
        height = sum(
            (self.sizeHintForRow(i) + 2) for i in range(len(self.files)))
        width = max(self.sizeHintForColumn(i) for i in range(len(self.files)))
        size.setHeight(height)
        size.setWidth(width + 2)
        return size

    def mouseMoveEvent(self, event):
        index = self.indexAt(
            QtCore.QPoint(int(event.position().x()),
                          int(event.position().y())))
        if index.isValid():
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        super().mouseMoveEvent(event)


class DropArtwork(QtWidgets.QWidget):
    """Muted image/drop mark used on an empty canvas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(130, 108)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.scale(self.width() / 180, self.height() / 150)
        color = QtGui.QColor('#666666')
        pen = QtGui.QPen(color, 4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setDashPattern([5, 5])
        painter.setPen(pen)
        painter.drawRoundedRect(QtCore.QRectF(25, 45, 130, 85), 2, 2)
        painter.setBrush(QtGui.QColor('#181818'))
        pen.setStyle(Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.drawRoundedRect(QtCore.QRectF(48, 18, 85, 70), 6, 6)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        mountain = QtGui.QPainterPath()
        mountain.moveTo(56, 79)
        mountain.lineTo(80, 52)
        mountain.lineTo(96, 67)
        mountain.lineTo(112, 45)
        mountain.lineTo(127, 79)
        mountain.closeSubpath()
        painter.drawPath(mountain)
        painter.drawEllipse(QtCore.QPointF(69, 37), 8, 8)


class WelcomeOverlay(MainControlsMixin, QtWidgets.QWidget):
    """Quiet empty-canvas prompt with only the two useful next actions."""

    def __init__(self, parent):
        super().__init__(parent)
        self.control_target = parent
        self.setObjectName('welcomeOverlay')
        self.setAutoFillBackground(True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.init_main_controls(main_window=parent.parent)

        self.files_view = RecentFilesView(self, parent)
        self.files_view.hide()
        self.artwork = DropArtwork(self)
        self.label = QtWidgets.QLabel(
            'Drag and drop images here\nor', self)
        self.label.setObjectName('welcomeMessage')
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.browse_button = QtWidgets.QPushButton('Browse', self)
        self.browse_button.setObjectName('welcomeBrowse')
        self.browse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_button.clicked.connect(parent.on_action_insert_images)
        self.help_button = QtWidgets.QPushButton('Help', self)
        self.help_button.setObjectName('welcomeHelp')
        self.help_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.help_button.clicked.connect(parent.on_action_help)

        center = QtWidgets.QVBoxLayout()
        center.setSpacing(10)
        center.addWidget(self.artwork, alignment=Qt.AlignmentFlag.AlignCenter)
        center.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignCenter)
        center.addWidget(
            self.browse_button, alignment=Qt.AlignmentFlag.AlignCenter)
        center.addWidget(
            self.help_button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addStretch(1)
        self.layout.addLayout(center)
        self.layout.addStretch(1)

    def disable_mouse_events(self):
        self.label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def enable_mouse_events(self):
        self.label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            on=False)

    def mousePressEvent(self, event):
        if self.mousePressEventMainControls(event):
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.mouseMoveEventMainControls(event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.mouseReleaseEventMainControls(event):
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if self.keyPressEventMainControls(event):
            return
        super().keyPressEvent(event)
