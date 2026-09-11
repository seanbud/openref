#!/usr/bin/env python3
"""Collect license texts for components shipped in an OpenRef binary."""

from argparse import ArgumentParser
from importlib import metadata
from pathlib import Path
import shutil
import sys


DISTRIBUTIONS = (
    'PyQt6', 'PyQt6-Qt6', 'PyQt6-sip', 'exif', 'plum-py', 'lxml',
    'rectangle-packer', 'pyinstaller',
)
LICENSE_MARKERS = ('license', 'copying', 'notice')


def copy_distribution_licenses(name, destination):
    distribution = metadata.distribution(name)
    copied = 0
    for entry in distribution.files or ():
        if not any(marker in entry.name.lower() for marker in LICENSE_MARKERS):
            continue
        source = Path(distribution.locate_file(entry))
        if not source.is_file():
            continue
        target = destination / f'{name}-{distribution.version}-{entry.name}'
        shutil.copyfile(source, target)
        copied += 1
    return copied


def copy_python_license(destination):
    candidates = (
        Path(sys.base_prefix) / 'LICENSE.txt',
        Path(sys.base_prefix) / 'lib' /
        f'python{sys.version_info.major}.{sys.version_info.minor}' /
        'LICENSE.txt',
    )
    for source in candidates:
        if source.is_file():
            shutil.copyfile(source, destination / 'Python-LICENSE.txt')
            return
    raise RuntimeError('Python LICENSE.txt was not found')


def main():
    parser = ArgumentParser()
    parser.add_argument('--output', type=Path,
                        default=Path('build/legal/third-party'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    missing = []
    for name in DISTRIBUTIONS:
        if copy_distribution_licenses(name, args.output) == 0:
            missing.append(name)
    copy_python_license(args.output)

    # PyQt6 metadata identifies GPLv3 but does not ship a license text. The
    # repository's exact GPLv3 text supplies it in the binary notice bundle.
    if 'PyQt6' in missing:
        shutil.copyfile('LICENSE', args.output / 'PyQt6-6.7.0-GPL-3.0.txt')
        missing.remove('PyQt6')
    if missing:
        raise RuntimeError('No license text found for: ' + ', '.join(missing))

    print(f'Collected license texts in {args.output}')


if __name__ == '__main__':
    main()
