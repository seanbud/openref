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
#colorDialog {
    background: #202126; border: 1px solid #090a0c; border-radius: 14px;
}
#colorDialogHeader { font-size: 15px; font-weight: 600; }
#colorPreview { border: 2px solid rgba(255, 255, 255, 90); }
#colorValueLabel { color: #aeb1b9; font-size: 10px; }
#colorSwatch {
    background: transparent; border: 2px solid transparent;
    border-radius: 8px;
}
#colorSwatch:checked { border-color: #ffffff; }
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
#welcomeOverlay { background: #181818; }
#welcomeHelp {
    background: transparent; border: none; color: #777777;
    text-decoration: underline; padding: 2px;
}
#welcomeMessage { color: #6e6e6e; font-size: 14px; }
#welcomeWordmark {
    color: #d9dadd; font-size: 28px; font-weight: 600;
    letter-spacing: 1px;
}
#welcomeShortcuts {
    color: #93969d; background: rgba(255, 255, 255, 8);
    border: 1px solid rgba(255, 255, 255, 18); border-radius: 8px;
    padding: 8px 12px; font-size: 11px;
}
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
        #welcomeOverlay { background: #0b1015; }
        #welcomeBrowse { background: #168da8; }
        #welcomeBrowse:hover { background: #20a4c1; }
        QPushButton { background: #243746; border-color: #3b5569; }
        QPushButton:hover { background: #2e485b; }
    """,
    'graphite': """
        /* Neutral, low-chroma workspace for color-critical reference work. */
    """,
    'sakura': """
        QWidget { color: #f5e9ef; }
        QMenuBar, QMenu, QDialog, QMessageBox { background: #2a2029; }
        QMenuBar::item:selected, QMenu::item:selected { background: #533845; }
        QMenu::separator { background: #5d3d4c; }
        #drawingToolbar {
            background: rgba(42, 29, 39, 248);
            border: 1px solid #090609;
            border-radius: 12px;
        }
        #drawingToolbar QToolButton:hover, #drawPopover QToolButton:hover,
        #windowChrome QToolButton:hover { background: #583744; }
        #drawingToolbar QToolButton:checked, #drawPopover QToolButton:checked,
        #windowChrome QToolButton:checked { background: #81485e; }
        #windowChrome {
            background: rgba(41, 27, 37, 250);
            border-bottom: 1px solid #090609;
        }
        #dialogCard, #commandPalette, #colorDialog {
            background: #2d222b;
            border: 1px solid #100a0e;
        }
        #commandSearch, #colorHex, #colorOpacity, QLineEdit, QSpinBox,
        QComboBox, QListView, QPlainTextEdit {
            background: #20171f; border-color: #694657;
        }
        #commandList::item:selected { background: #80465c; }
        #BeeNotification { background: rgba(45, 31, 42, 245); }
        #notificationShortcut { background: #3a2632; border-color: #75495d; }
        #primaryButton { background: #ce668c; }
        #primaryButton:hover { background: #df789d; }
        #welcomeOverlay { background: #151015; }
        #welcomeBrowse { background: #ce668c; }
        #welcomeBrowse:hover { background: #df789d; }
        QPushButton { background: #4a313e; border-color: #70495b; }
        QPushButton:hover { background: #5b3b4a; }
    """,
    'ocean': """
        QWidget { color: #e5f4f5; }
        QMenuBar, QMenu, QDialog, QMessageBox { background: #10262c; }
        QMenuBar::item:selected, QMenu::item:selected { background: #1d4850; }
        QMenu::separator { background: #285862; }
        #drawingToolbar {
            background: rgba(11, 35, 42, 248);
            border: 1px solid #02090b;
            border-radius: 12px;
        }
        #drawingToolbar QToolButton:hover, #drawPopover QToolButton:hover,
        #windowChrome QToolButton:hover { background: #1c4b54; }
        #drawingToolbar QToolButton:checked, #drawPopover QToolButton:checked,
        #windowChrome QToolButton:checked { background: #24727b; }
        #windowChrome {
            background: rgba(10, 31, 38, 250);
            border-bottom: 1px solid #02090b;
        }
        #dialogCard, #commandPalette, #colorDialog {
            background: #112b32; border: 1px solid #041014;
        }
        #commandSearch, #colorHex, #colorOpacity, QLineEdit, QSpinBox,
        QComboBox, QListView, QPlainTextEdit {
            background: #0b2026; border-color: #2c626b;
        }
        #commandList::item:selected { background: #1b6871; }
        #BeeNotification { background: rgba(10, 34, 41, 245); }
        #notificationShortcut { background: #123942; border-color: #2d6972; }
        #primaryButton { background: #28a9ad; }
        #primaryButton:hover { background: #35bec1; }
        #welcomeOverlay { background: #071317; }
        #welcomeBrowse { background: #28a9ad; }
        #welcomeBrowse:hover { background: #35bec1; }
        QPushButton { background: #193f47; border-color: #2e6069; }
        QPushButton:hover { background: #21515b; }
    """,
    'forest': """
        QWidget { color: #edf1e6; }
        QMenuBar, QMenu, QDialog, QMessageBox { background: #20291f; }
        QMenuBar::item:selected, QMenu::item:selected { background: #3c4d37; }
        QMenu::separator { background: #4a5d44; }
        #drawingToolbar {
            background: rgba(27, 37, 27, 248);
            border: 1px solid #070a07;
            border-radius: 12px;
        }
        #drawingToolbar QToolButton:hover, #drawPopover QToolButton:hover,
        #windowChrome QToolButton:hover { background: #40513a; }
        #drawingToolbar QToolButton:checked, #drawPopover QToolButton:checked,
        #windowChrome QToolButton:checked { background: #63784e; }
        #windowChrome {
            background: rgba(27, 36, 26, 250);
            border-bottom: 1px solid #070a07;
        }
        #dialogCard, #commandPalette, #colorDialog {
            background: #263125; border: 1px solid #0b0e0a;
        }
        #commandSearch, #colorHex, #colorOpacity, QLineEdit, QSpinBox,
        QComboBox, QListView, QPlainTextEdit {
            background: #192118; border-color: #53664b;
        }
        #commandList::item:selected { background: #586f48; }
        #BeeNotification { background: rgba(32, 43, 31, 245); }
        #notificationShortcut { background: #33422f; border-color: #607355; }
        #primaryButton { background: #7d9b5c; }
        #primaryButton:hover { background: #8ead69; }
        #welcomeOverlay { background: #111711; }
        #welcomeBrowse { background: #718d54; }
        #welcomeBrowse:hover { background: #829f61; }
        QPushButton { background: #3b4a36; border-color: #5b6b51; }
        QPushButton:hover { background: #485a41; }
    """,
    'paper': """
        QWidget { color: #302d29; }
        QMenuBar, QMenu, QDialog, QMessageBox { background: #eee8dc; }
        #openRefWindow { background: #1b1916; }
        QMenuBar::item:selected, QMenu::item:selected { background: #d9d0c0; }
        QMenu { border-color: #9f9584; }
        QMenu::separator { background: #c8beae; }
        #drawingToolbar {
            background: rgba(38, 47, 55, 248);
            border: 1px solid #080a0c;
            border-radius: 12px;
        }
        #drawingToolbar QToolButton:hover, #drawPopover QToolButton:hover,
        #windowChrome QToolButton:hover { background: #465866; }
        #drawingToolbar QToolButton:checked, #drawPopover QToolButton:checked,
        #windowChrome QToolButton:checked { background: #607886; }
        #windowChrome {
            background: rgba(231, 224, 211, 250);
            border-bottom: 1px solid #8f8678;
        }
        #dialogCard, #commandPalette, #colorDialog {
            background: #f3eee5; border-color: #9f9584;
        }
        #commandSearch, #colorHex, #colorOpacity, QLineEdit, QSpinBox,
        QComboBox, QListView, QPlainTextEdit {
            background: #fffaf1; border-color: #b7ad9d;
        }
        #commandList::item:selected { background: #c7d8dc; color: #24343a; }
        #BeeNotification { background: rgba(242, 237, 227, 245); }
        #notificationText, #notificationIcon { color: #302d29; }
        #notificationShortcut {
            color: #42545b; background: #ded8cd; border-color: #aaa194;
        }
        #dialogClose { color: #302d29; }
        #primaryButton { background: #477f91; }
        #primaryButton:hover { background: #5793a5; }
        #welcomeOverlay { background: #d1c9bd; }
        #welcomeMessage, #welcomeHelp { color: #71695f; }
        #welcomeBrowse { background: #477f91; }
        #welcomeBrowse:hover { background: #5793a5; }
        QPushButton { background: #ddd5c8; border-color: #ada394; }
        QPushButton:hover { background: #cec4b5; }
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
        #welcomeOverlay { background: #d9dde0; }
        #welcomeMessage, #welcomeHelp { color: #687078; }
        QPushButton { background: #dde3e8; border-color: #aeb8c0; }
        QPushButton:hover { background: #ccd6dd; }
    """,
}


def available_themes():
    """Return stable theme identifiers and their user-facing names."""

    return (
        ('midnight', 'OpenRef Midnight'),
        ('graphite', 'Graphite'),
        ('sakura', 'Sakura'),
        ('ocean', 'Deep Ocean'),
        ('forest', 'Forest'),
        ('paper', 'Warm Paper'),
        ('light', 'Soft Light'),
    )


CANVAS_COLORS = {
    'midnight': ('#0b1015', '#121b23'),
    'graphite': ('#121212', '#1a1a1a'),
    'sakura': ('#151015', '#211820'),
    'ocean': ('#071317', '#0d2228'),
    'forest': ('#111711', '#1c251b'),
    'paper': ('#c8c0b4', '#e6dfd3'),
    'light': ('#d9dde0', '#edf0f2'),
}


def canvas_colors(theme):
    """Return dead-space and used-space colors for a theme."""

    return CANVAS_COLORS.get(theme, CANVAS_COLORS['midnight'])


def apply_theme(app, theme='midnight'):
    """Apply an OpenRef theme to a QApplication."""

    theme = theme if theme in THEME_STYLESHEETS else 'midnight'
    app.setStyle('Fusion')
    app.setFont(QtGui.QFont('Helvetica', 13))
    app.setProperty('openrefTheme', theme)
    app.setStyleSheet(BASE_STYLESHEET + THEME_STYLESHEETS[theme])
