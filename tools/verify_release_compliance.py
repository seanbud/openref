#!/usr/bin/env python3
"""Verify that required legal and provenance material is present."""

from importlib import metadata
from pathlib import Path


REQUIRED = (
    'LICENSE', 'NOTICE', 'SOURCE_CODE.txt', 'THIRD_PARTY_NOTICES.md',
    'CONTRIBUTORS.md', 'ASSET_PROVENANCE.md',
    'requirements/runtime-release.txt',
)


def locked_versions():
    result = {}
    lock_text = Path('requirements/runtime-release.txt').read_text()
    for line in lock_text.splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            name, version = line.split('==', 1)
            result[name] = version
    return result


def verify_source_bundle_pins(versions):
    """Keep corresponding-source URLs aligned with the release runtime lock."""
    source_bundle = Path('tools/build_source_bundle.py').read_text()
    for name in ('PyQt6', 'PyQt6-sip'):
        expected = versions.get(name)
        if expected and f"'{name}': '{expected}'" not in source_bundle:
            raise SystemExit(
                f'{name}: source-bundle pin does not match runtime lock')

    qt_version = versions.get('PyQt6-Qt6')
    if qt_version:
        expected_fragments = (
            f'/6.7/{qt_version}/',
            f'qtbase-everywhere-src-{qt_version}',
            f'qtimageformats-everywhere-src-{qt_version}',
            f'qtsvg-everywhere-src-{qt_version}',
        )
        missing = [fragment for fragment in expected_fragments
                   if fragment not in source_bundle]
        if missing:
            raise SystemExit(
                'Qt source-bundle pins do not match runtime lock: '
                + ', '.join(missing))


def main():
    absent = [path for path in REQUIRED if not Path(path).is_file()]
    if absent:
        raise SystemExit('Missing release files: ' + ', '.join(absent))
    versions = locked_versions()
    verify_source_bundle_pins(versions)
    for name, expected in versions.items():
        actual = metadata.version(name)
        if actual != expected:
            message = f'{name}: installed {actual}, expected {expected}'
            raise SystemExit(message)
    legal = Path('build/legal/third-party')
    if not legal.is_dir() or not any(legal.iterdir()):
        raise SystemExit('Third-party license collection is empty')
    print('Release compliance inputs verified')


if __name__ == '__main__':
    main()
