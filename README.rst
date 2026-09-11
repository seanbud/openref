OpenRef
*******

.. image:: beeref/assets/openref.png
   :width: 96
   :alt: OpenRef application icon

OpenRef is a free and open-source reference canvas for artists and visual
creators. It is a community fork of `BeeRef <https://github.com/rbreu/beeref>`_
with an original, themeable canvas-first interface and efficient drawing,
arrangement, and navigation workflows.

OpenRef is an independent project and is not affiliated with or endorsed by
proprietary reference-board products.

Highlights
----------

* Arrange, scale, crop, rotate, flip, and annotate reference images.
* Draw freehand marks, lines, arrows, rectangles, and ellipses.
* Work through a compact canvas-first interface with keyboard shortcuts.
* Choose an OpenRef theme and place drawing controls in any canvas corner.
* Save complete boards as portable ``.bee`` files.

Install
-------

Download the macOS or Windows build from
`Releases <https://github.com/seanbud/openref/releases>`_, or run from source
with Python 3.9–3.12::

  git clone https://github.com/seanbud/openref.git
  cd openref
  python3 -m venv .venv
  .venv/bin/python -m pip install -e .
  .venv/bin/openref

On Windows, use ``.venv\Scripts\python`` and ``.venv\Scripts\openref``.

OpenRef source is released under GPL-3.0-or-later. Official binaries include
PyQt6 and are distributed under GPL-3.0-only. The original BeeRef project and
Rebecca Breu deserve full credit for the foundation this fork builds upon.

See `SOURCE_CODE.txt <SOURCE_CODE.txt>`_ for corresponding source access,
`NOTICE <NOTICE>`_ for attribution, and `COMPANY_USE.md <COMPANY_USE.md>`_ for
practical organizational and contractor deployment guidance.
Third-party components and licenses are listed in
`THIRD_PARTY_NOTICES.md <THIRD_PARTY_NOTICES.md>`_.
