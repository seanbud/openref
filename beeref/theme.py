"""Original OpenRef themes for the canvas-first interface."""

from PyQt6 import QtGui


BASE_STYLESHEET = """
QWidget {
    color: #e8e9ed;
    font-family: "Helvetica";
    font-size: 11px;
}
QMenuBar, QMenu, QDialog, QMessageBox {
    background: #202020;
    color: #e8e9ed;
}
#openRefWindow { background: #000000; }
QMenuBar::item { padding: 5px 8px; border-radius: 4px; }
QMenuBar::item:selected, QMenu::item:selected { background: #3b3b3b; }
QMenu { border: 1px solid #000000; padding: 4px; }
QMenu::item { padding: 5px 22px 5px 8px; border-radius: 4px; }
QMenu::separator { height: 1px; background: #3a3c43; margin: 5px 8px; }
QToolTip {
    background: #111216; color: #f4f4f5; border: 1px solid #444750;
    padding: 4px; border-radius: 4px;
}
#drawingToolbar {
    background: rgba(35, 35, 35, 248);
    border: 1px solid #000000;
    border-radius: 9px;
}
#drawingToolbar QToolButton, #drawPopover QToolButton,
#windowChrome QToolButton {
    background: transparent; border: none; border-radius: 5px;
}
#drawingToolbar QToolButton:hover, #drawPopover QToolButton:hover,
#windowChrome QToolButton:hover { background: #404040; }
#drawingToolbar QToolButton:checked, #drawPopover QToolButton:checked,
#windowChrome QToolButton:checked {
    background: #585858;
}
#commandSearch {
    background: #292b31; border: 1px solid #454851; border-radius: 5px;
    padding: 4px 6px;
}
#commandPalette {
    background: #202126; border: 1px solid #000; border-radius: 8px;
}
#commandSearch { padding: 7px 9px; font-size: 12px; }
#commandList { background: transparent; border: none; outline: none; }
#commandList::item { padding: 7px 8px; border-radius: 5px; }
#commandList::item:selected { background: #35696b; color: white; }
#BeeNotification {
    background: rgba(29, 30, 34, 245);
    border: 1px solid #000000;
    border-radius: 7px;
}
#notificationIcon {
    color: #d8dadf; font-size: 15px; font-weight: 600;
}
#notificationText {
    color: #f0f1f3; font-size: 11px; font-weight: 600;
}
#notificationShortcut {
    color: #aeb1b9; font-size: 9px;
    background: #27292f; border: 1px solid #41444c;
    border-radius: 4px; padding: 2px 4px;
}
#windowChrome {
    background: rgba(32, 32, 32, 250);
    border-bottom: 1px solid #000000;
}
#dialogCard {
    background: #232323;
    border: 1px solid #111111;
    border-radius: 9px;
}
#dialogTitle { font-size: 15px; font-weight: 500; }
#dialogMessage { font-size: 13px; }
#dialogClose {
    background: transparent; border: none; color: #eeeeef;
    font-size: 21px; padding: 0;
}
#dialogClose:hover { background: #3a3a3a; border-radius: 6px; }
#colorHex, #colorOpacity {
    background: #181818; border: none; border-radius: 5px;
    padding: 5px; font-size: 12px;
}
#primaryButton, #dangerButton, #secondaryButton {
    min-width: 72px; min-height: 30px; border: none;
    border-radius: 5px; font-size: 13px; font-weight: 500;
}
#primaryButton { background: #0996c2; color: white; }
#primaryButton:hover { background: #10a8d7; }
#dangerButton { background: #df315d; color: white; }
#dangerButton:hover { background: #ed426b; }
#secondaryButton { background: #383838; color: #eeeeef; }
#secondaryButton:hover { background: #454545; }
#welcomeBrowse {
    background: #0996c2; border: none; color: white;
    border-radius: 5px; padding: 7px 16px; font-size: 12px;
}
#welcomeBrowse:hover { background: #10a8d7; }
#welcomeOverlay { background: #181818; }
#welcomeHelp {
    background: transparent; border: none; color: #777777;
    text-decoration: underline; padding: 2px;
}
#welcomeMessage { color: #6e6e6e; font-size: 14px; }
QPushButton {
    background: #34363d; border: 1px solid #484b54; border-radius: 7px;
    padding: 5px 9px;
}
QPushButton:hover { background: #40434b; }
QLineEdit, QSpinBox, QComboBox, QListView, QPlainTextEdit {
    background: #292b31; border: 1px solid #454851; border-radius: 6px;
    padding: 5px;
}
"""


THEME_STYLESHEETS = {
    'midnight': """
        QWidget { color: #e7edf4; }
        QMenuBar, QMenu, QDialog, QMessageBox { background: #18212a; }
        QMenuBar::item:selected, QMenu::item:selected { background: #294052; }
        QMenu::separator { background: #314353; }
        #drawingToolbar {
            background: rgba(17, 27, 36, 248);
            border: 1px solid #020608;
            border-radius: 12px;
        }
        #drawingToolbar QToolButton:hover, #drawPopover QToolButton:hover,
        #windowChrome QToolButton:hover { background: #294052; }
        #drawingToolbar QToolButton:checked, #drawPopover QToolButton:checked,
        #windowChrome QToolButton:checked { background: #35647a; }
        #windowChrome {
            background: rgba(15, 25, 34, 250);
            border-bottom: 1px solid #020608;
        }
        #dialogCard, #commandPalette {
            background: #18232d;
            border: 1px solid #060a0d;
        }
        #commandSearch, QLineEdit, QSpinBox, QComboBox, QListView,
        QPlainTextEdit { background: #111a22; border-color: #385064; }
        #commandList::item:selected { background: #236d78; }
        #BeeNotification { background: rgba(17, 27, 36, 245); }
        #notificationShortcut { background: #12232e; border-color: #315266; }
        QPushButton { background: #243746; border-color: #3b5569; }
        QPushButton:hover { background: #2e485b; }
    """,
    'graphite': """
        /* Neutral, low-chroma workspace for color-critical reference work. */
    """,
    'light': """
        QWidget { color: #20252b; }
        QMenuBar, QMenu, QDialog, QMessageBox { background: #eceff2; }
        #openRefWindow { background: #111111; }
        QMenuBar::item:selected, QMenu::item:selected { background: #d4dce3; }
        QMenu { border-color: #9ba6af; }
        QMenu::separator { background: #c6cdd3; }
        #drawingToolbar {
            background: rgba(27, 38, 47, 248);
            border: 1px solid #000000;
            border-radius: 12px;
        }
        #drawingToolbar QToolButton:hover, #drawPopover QToolButton:hover,
        #windowChrome QToolButton:hover { background: #3b5263; }
        #drawingToolbar QToolButton:checked, #drawPopover QToolButton:checked,
        #windowChrome QToolButton:checked { background: #347383; }
        #windowChrome { background: rgba(235, 239, 242, 250); }
        #dialogCard, #commandPalette {
            background: #f2f4f6;
            border-color: #9ba6af;
        }
        #commandSearch, QLineEdit, QSpinBox, QComboBox, QListView,
        QPlainTextEdit { background: #ffffff; border-color: #aab4bc; }
        #commandList::item:selected { background: #b8dbe0; color: #172126; }
        #BeeNotification { background: rgba(239, 242, 244, 245); }
        #notificationText, #notificationIcon { color: #20252b; }
        #notificationShortcut {
            color: #394650; background: #dde4e9; border-color: #aab6bf;
        }
        #dialogClose { color: #20252b; }
        QPushButton { background: #dde3e8; border-color: #aeb8c0; }
        QPushButton:hover { background: #ccd6dd; }
    """,
}


def available_themes():
    """Return stable theme identifiers and their user-facing names."""

    return (
        ('midnight', 'OpenRef Midnight'),
        ('graphite', 'Graphite'),
        ('light', 'Soft Light'),
    )


def apply_theme(app, theme='midnight'):
    """Apply an OpenRef theme to a QApplication."""

    theme = theme if theme in THEME_STYLESHEETS else 'midnight'
    app.setStyle('Fusion')
    app.setFont(QtGui.QFont('Helvetica', 13))
    app.setStyleSheet(BASE_STYLESHEET + THEME_STYLESHEETS[theme])
