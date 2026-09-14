Releasing OpenRef
=================

The ``release installers`` GitHub Actions workflow builds:

* an Apple Silicon ``OpenRef.app`` packaged as a DMG on an arm64 macOS runner;
* a 64-bit Windows executable packaged with Inno Setup; and
* a GitHub Release containing both installers when the workflow is triggered by
  a version tag such as ``v0.4.0-beta.1`` or ``v0.4.0``.

The workflow can also be run manually from the Actions page. Manual runs upload
the installers as workflow artifacts without creating a GitHub Release.

macOS signing and notarization
------------------------------

Manual testing does not require Apple credentials: the macOS job creates an
ad-hoc-signed DMG. For a distributable notarized build, configure these
repository Actions secrets:

``MACOS_CERTIFICATE``
  A base64-encoded Developer ID Application ``.p12`` certificate.

``MACOS_CERTIFICATE_PASSWORD``
  The certificate export password.

``MACOS_CODESIGN_IDENTITY``
  The full Developer ID Application identity.

``APPLE_ID``, ``APPLE_TEAM_ID``, ``APPLE_APP_PASSWORD``
  Credentials used by Apple's ``notarytool``. The app password should be an
  app-specific password rather than the Apple ID password.

Creating a release
------------------

After tests pass and the version has been updated, create and push a version
tag::

  git tag v0.4.0-beta.1
  git push origin v0.4.0-beta.1

The workflow publishes the two installers only after both platform builds
succeed. Tags containing a hyphen are published as prereleases.

Compliance checklist
--------------------

Every public installer must remain accompanied by its same-build
``OpenRef-Corresponding-Source`` archive for as long as the installer is
offered. The workflow deliberately fails before packaging if runtime versions,
project notices, or collected third-party license texts are missing.

Before publishing a tag:

* update and test ``requirements/runtime-release.txt`` deliberately;
* review ``THIRD_PARTY_NOTICES.md`` and every collected license;
* confirm the source bundle contains the exact OpenRef revision and upstream
  sources listed by ``SOURCE_MANIFEST.json``;
* verify the macOS and Windows checksum files;
* retain the source archive beside both installers; and
* withdraw installers immediately if their corresponding source or notices are
  missing.

Linux AppImage distribution is intentionally disabled pending a separate audit
of the base image and copied system libraries.
