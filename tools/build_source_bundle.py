#!/usr/bin/env python3
"""Build a same-release corresponding-source archive for OpenRef binaries."""

from argparse import ArgumentParser
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
from urllib.request import urlopen


PYPI_SOURCES = {
    'exif': '1.6.0',
    'lxml': '5.1.0',
    'plum-py': '0.8.7',
    'PyQt6': '6.7.0',
    'PyQt6-sip': '13.12.0',
    'rectangle-packer': '2.0.2',
    'pyinstaller': '6.6.0',
}
DIRECT_SOURCES = {
    'Python-3.11.9.tgz':
        'https://www.python.org/ftp/python/3.11.9/Python-3.11.9.tgz',
    'qtbase-everywhere-src-6.7.0.tar.xz':
        'https://download.qt.io/archive/qt/6.7/6.7.0/submodules/'
        'qtbase-everywhere-src-6.7.0.tar.xz',
    'qtimageformats-everywhere-src-6.7.0.tar.xz':
        'https://download.qt.io/archive/qt/6.7/6.7.0/submodules/'
        'qtimageformats-everywhere-src-6.7.0.tar.xz',
    'qtsvg-everywhere-src-6.7.0.tar.xz':
        'https://download.qt.io/archive/qt/6.7/6.7.0/submodules/'
        'qtsvg-everywhere-src-6.7.0.tar.xz',
}


def download(url, target):
    digest = hashlib.sha256()
    with urlopen(url) as response, target.open('wb') as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
            digest.update(chunk)
    return digest.hexdigest()


def pypi_sdist_url(name, version):
    with urlopen(f'https://pypi.org/pypi/{name}/{version}/json') as response:
        release = json.load(response)
    sdists = [
        item for item in release['urls']
        if item['packagetype'] == 'sdist'
    ]
    if len(sdists) != 1:
        raise RuntimeError(f'Expected one sdist for {name} {version}')
    item = sdists[0]
    return item['filename'], item['url'], item['digests']['sha256']


def main():
    parser = ArgumentParser()
    parser.add_argument('--revision', default='HEAD')
    parser.add_argument('--output', type=Path, default=Path('dist/source'))
    args = parser.parse_args()
    revision = subprocess.check_output(
        ['git', 'rev-parse', args.revision], text=True).strip()
    args.output.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temporary:
        bundle_name = f'OpenRef-Corresponding-Source-{revision[:12]}'
        root = Path(temporary) / bundle_name
        downloads = root / 'upstream-sources'
        downloads.mkdir(parents=True)
        manifest = {'openref_revision': revision, 'sources': []}

        app_archive = root / f'OpenRef-{revision[:12]}.tar.gz'
        with app_archive.open('wb') as output:
            subprocess.run(
                ['git', 'archive', '--format=tar.gz', revision], check=True,
                stdout=output)
        manifest['sources'].append({
            'file': app_archive.name,
            'sha256': hashlib.sha256(app_archive.read_bytes()).hexdigest(),
            'source': 'OpenRef Git revision',
        })

        for name, version in PYPI_SOURCES.items():
            filename, url, expected = pypi_sdist_url(name, version)
            target = downloads / filename
            actual = download(url, target)
            if actual != expected:
                raise RuntimeError(f'Checksum mismatch for {filename}')
            manifest['sources'].append(
                {'file': filename, 'sha256': actual, 'source': url})

        for filename, url in DIRECT_SOURCES.items():
            target = downloads / filename
            actual = download(url, target)
            manifest['sources'].append(
                {'file': filename, 'sha256': actual, 'source': url})

        for filename in ('LICENSE', 'NOTICE', 'SOURCE_CODE.txt',
                         'THIRD_PARTY_NOTICES.md', 'CONTRIBUTORS.md',
                         'ASSET_PROVENANCE.md'):
            shutil.copyfile(filename, root / filename)
        shutil.copyfile('requirements/runtime-release.txt',
                        root / 'runtime-release.txt')
        (root / 'SOURCE_MANIFEST.json').write_text(
            json.dumps(manifest, indent=2) + '\n', encoding='utf-8')

        archive = args.output / (
            f'OpenRef-Corresponding-Source-{revision[:12]}.tar.gz')
        with tarfile.open(archive, 'w:gz') as bundle:
            bundle.add(root, arcname=root.name)
        print(archive)


if __name__ == '__main__':
    main()
