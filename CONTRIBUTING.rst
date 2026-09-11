OpenRef — Notes For Developers
==============================

OpenRef is written in Python and PyQt6. It remains compatible with BeeRef's
``.bee`` scene format and keeps the internal ``beeref`` Python package name.


Developing
----------

Optional step: Use pyenv to create a virtual environment::

  pyenv install -v 3.11
  pyenv virtualenv 3.11 openref

Once the vitrual environment is set up, you can enter it with::

  pyenv activate openref


Clone the repository and install OpenRef and its dependencies::

  git clone https://github.com/seanbud/openref.git
  cd openref
  pip install -e .

Install additional development requirements::

  pip install -r requirements/dev.txt

Run unittests with::

  pytest --cov .

This will also generate a coverage report:  ``htmlcov/index.html``.

Run codechecks with::

  flake8 .

Beeref files are sqlite databases, so they can be inspected with any sqlite browser.

For debugging options, run::

  openref --help


Building the app
----------------

To build the app, run::

  pyinstaller OpenRef.spec

You will find the generated executable in the folder ``dist``.


Release installers
------------------

Release installers are built by ``.github/workflows/release-installers.yml``.
See ``RELEASING.rst`` for the release and signing workflow.
