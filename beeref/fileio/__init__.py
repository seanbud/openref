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
import os
import tempfile
from types import SimpleNamespace

from PyQt6 import QtCore

from beeref import commands
from beeref.fileio.errors import BeeFileIOError
from beeref.fileio.image import load_image
from beeref.fileio.sql import SQLiteIO, is_bee_file, is_legacy_board
from beeref.items import BeePixmapItem


__all__ = [
    'is_bee_file',
    'is_legacy_board',
    'load_bee',
    'save_bee',
    'load_images',
    'ThreadedLoader',
    'BeeFileIOError',
]

logger = logging.getLogger(__name__)


def load_bee(filename, scene, worker=None):
    """Load BeeRef native file."""
    logger.info(f'Loading from file {filename}...')
    io = SQLiteIO(filename, scene, readonly=True, worker=worker)
    return io.read()


def save_bee(filename, scene, create_new=False, worker=None):
    """Save BeeRef native file."""
    logger.info(f'Saving to file {filename}...')
    logger.debug(f'Create new: {create_new}')
    if is_legacy_board(filename):
        error = 'Legacy boards must be saved as a new .openref file.'
        if worker:
            worker.finished.emit(filename, [error])
            return
        raise BeeFileIOError(msg=error, filename=filename)
    if not create_new:
        io = SQLiteIO(filename, scene, worker=worker)
        io.write()
        return

    # Build Save As fully before replacing an existing destination. A failed
    # encode or canceled write must leave the previous file untouched.
    previous_ids = [(item, item.save_id) for item in scene.items_for_save()]
    result = []
    proxy = None
    if worker:
        proxy = SimpleNamespace(
            begin_processing=worker.begin_processing,
            progress=worker.progress,
            finished=SimpleNamespace(emit=lambda name, errors:
                                     result.extend(errors)),
        )
        # Forward cancellation dynamically instead of snapshotting its value.

        class SaveProgress:
            def __getattr__(self, name):
                return getattr(worker if name == 'canceled' else proxy, name)
        proxy_worker = SaveProgress()
    else:
        proxy_worker = None
    try:
        directory = os.path.dirname(os.path.abspath(filename))
        with tempfile.TemporaryDirectory(prefix='.openref-',
                                         dir=directory) as scratch:
            temporary = os.path.join(scratch, 'board.openref')
            io = SQLiteIO(temporary, scene, True, worker=proxy_worker)
            io.write()
            io._close_connection()
            if result:
                raise ValueError('; '.join(result))
            os.replace(temporary, filename)
    except Exception as error:
        for item, save_id in previous_ids:
            item.save_id = save_id
        if worker:
            worker.finished.emit(filename, [str(error)])
            return
        raise BeeFileIOError(msg=str(error), filename=filename) from error
    if worker:
        worker.finished.emit(filename, [])
    logger.info('End save')


def load_images(filenames, pos, scene, worker):
    """Add images to existing scene."""

    errors = []
    items = []
    worker.begin_processing.emit(len(filenames))
    for i, filename in enumerate(filenames):
        logger.info(f'Loading image from file {filename}')
        img, filename = load_image(filename)
        worker.progress.emit(i)
        if img.isNull():
            logger.info(f'Could not load file {filename}')
            errors.append(filename)
            continue

        item = BeePixmapItem(img, filename)
        item.set_pos_center(pos)
        scene.add_item_later({'item': item, 'type': 'pixmap'}, selected=True)
        items.append(item)
        if worker.canceled:
            break
        # Give main thread time to process items:
        worker.msleep(10)

    scene.undo_stack.push(
        commands.InsertItems(scene, items, ignore_first_redo=True))
    worker.finished.emit('', errors)


class ThreadedIO(QtCore.QThread):
    """Dedicated thread for loading and saving."""

    progress = QtCore.pyqtSignal(int)
    finished = QtCore.pyqtSignal(str, list)
    begin_processing = QtCore.pyqtSignal(int)
    user_input_required = QtCore.pyqtSignal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.kwargs['worker'] = self
        self.canceled = False

    def run(self):
        self.func(*self.args, **self.kwargs)

    def on_canceled(self):
        self.canceled = True
