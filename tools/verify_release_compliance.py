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


def main():
    absent = [path for path in REQUIRED if not Path(path).is_file()]
    if absent:
        raise SystemExit('Missing release files: ' + ', '.join(absent))
    for name, expected in locked_versions().items():
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
