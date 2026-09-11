# -*- mode: python ; coding: utf-8 -*-

import os
from os.path import join
import sys

from beeref import constants


block_cipher = None
appname = f'{constants.APPNAME}-{constants.VERSION}'
legal_datas = [
    ('LICENSE', '.'),
    ('NOTICE', '.'),
    ('SOURCE_CODE.txt', '.'),
    ('THIRD_PARTY_NOTICES.md', '.'),
    ('CONTRIBUTORS.md', '.'),
    ('ASSET_PROVENANCE.md', '.'),
]
third_party_licenses = join('build', 'legal', 'third-party')
if os.path.isdir(third_party_licenses):
    legal_datas.append((third_party_licenses, 'THIRD_PARTY_LICENSES'))
build_provenance = join('build', 'legal', 'build-provenance.json')
if os.path.isfile(build_provenance):
    legal_datas.append((build_provenance, '.'))

if sys.platform.startswith('win'):
    icon = 'openref.ico'
    version_file = join('packaging', 'windows', 'version_info.txt')
else:
    icon = 'openref.icns'  # For macOS; ignored on Linux
    version_file = None


a = Analysis(
    [join('beeref', '__main__.py')],
    pathex=[os.getcwd()],
    binaries=[],
    datas=[
        (join('beeref', 'documentation'), join('beeref', 'documentation')),
        (join('beeref', 'assets', 'openref.png'), join('beeref', 'assets')),
    ] + legal_datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt6.QtBluetooth',
        'PyQt6.QtDBus',
        'PyQt6.QtDesigner',
        'PyQt6.QtHelp',
        'PyQt6.QtMultimedia',
        'PyQt6.QtMultimediaWidgets',
        'PyQt6.QtNetwork',
        'PyQt6.QtNetworkAuth',
        'PyQt6.QtNfc',
        'PyQt6.QtOpenGL',
        'PyQt6.QtOpenGLWidgets',
        'PyQt6.QtPdf',
        'PyQt6.QtPdfWidgets',
        'PyQt6.QtPositioning',
        'PyQt6.QtQml',
        'PyQt6.QtQuick',
        'PyQt6.QtQuick3D',
        'PyQt6.QtRemoteObjects',
        'PyQt6.QtSensors',
        'PyQt6.QtSerialPort',
        'PyQt6.QtSpatialAudio',
        'PyQt6.QtSql',
        'PyQt6.QtTest',
        'PyQt6.QtWebChannel',
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebSockets'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False)

# Qt's generic hook discovers optional plugins that OpenRef never uses. Keep
# the common image formats, including SVG, but do not ship PDF input or the
# network-dependent touch plugin and their otherwise-unused libraries.
optional_qt_fragments = (
    'plugins/imageformats/libqpdf',
    'plugins/imageformats/qpdf',
    'plugins/generic/libqtuiotouch',
    'plugins/generic/qtuiotouch',
    'QtPdf.framework',
    'QtNetwork.framework',
    'Qt6Pdf.dll',
    'Qt6Network.dll',
)
a.binaries = [
    entry for entry in a.binaries
    if not any(fragment in entry[0].replace('\\', '/')
               for fragment in optional_qt_fragments)
]
a.datas = [
    entry for entry in a.datas
    if not any(fragment in entry[0].replace('\\', '/')
               for fragment in optional_qt_fragments)
]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=appname,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=os.environ.get('OPENREF_TARGET_ARCH'),
    codesign_identity=os.environ.get('APPLE_CODESIGN_IDENTITY'),
    entitlements_file=(join('packaging', 'macos', 'entitlements.plist')
                       if sys.platform == 'darwin' else None),
    version=version_file,
    icon=join('beeref', 'assets', icon))

if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name=f'{constants.APPNAME}.app',
        icon=join('beeref', 'assets', icon),
        bundle_identifier='org.openref.OpenRef',
        version=f'{constants.VERSION}',
        info_plist={
            'CFBundleDocumentTypes': [
                {
                    'CFBundleTypeExtensions': [ 'bee' ],
                    'CFBundleTypeRole': 'Viewer'
                }
            ]
        })
