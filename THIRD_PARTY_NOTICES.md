# Third-party software in official OpenRef binaries

Official OpenRef binaries include the components below. Their complete license
texts are installed in `THIRD_PARTY_LICENSES`. Exact versions and source
archives for each build are included in its corresponding-source archive.

| Component | Version | License |
| --- | --- | --- |
| Python | 3.11.9 | Python Software Foundation License |
| PyQt6 | 6.7.0 | GNU GPL version 3 only |
| Qt | 6.7.0 | GNU LGPL version 3 / GNU GPL version 3, plus component notices |
| PyQt6-sip | 13.12.0 | BSD 2-Clause |
| exif | 1.6.0 | MIT |
| plum-py | 0.8.7 | MIT |
| lxml | 5.1.0 | BSD 3-Clause and bundled notices |
| rectangle-packer | 2.0.2 | MIT |

OpenRef uses Qt through PyQt6. Qt is Copyright © The Qt Company Ltd. and
other contributors. Users may replace the Qt shared libraries in an unpacked
application bundle with a compatible build, subject to the applicable license.

PyInstaller is used to produce the executables under its bootloader exception;
it does not impose its GPL terms on the produced application.
