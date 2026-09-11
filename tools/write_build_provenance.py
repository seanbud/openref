#!/usr/bin/env python3
"""Record reproducible metadata for an official OpenRef build."""

import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    output = Path('build/legal/build-provenance.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    freeze = subprocess.check_output(
        [sys.executable, '-m', 'pip', 'freeze'], text=True).splitlines()
    revision = subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], text=True).strip()
    record = {
        'openref_revision': revision,
        'python': platform.python_version(),
        'platform': platform.platform(),
        'machine': platform.machine(),
        'github_runner_image': os.environ.get('ImageOS', ''),
        'github_runner_version': os.environ.get('ImageVersion', ''),
        'runtime_lock_sha256': sha256('requirements/runtime-release.txt'),
        'build_lock_sha256': sha256('requirements/build.txt'),
        'installed_packages': freeze,
    }
    output.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()
