.. _playwright:

##################
Browser.Playwright
##################


New Playwright based browser automation library. Upstream examples,
docs and issue tracker available at `github.`_

.. _github.: https://github.com/marketsquare/robotframework-browser#robotframework-browser

Install instructions
====================

The Playwright based browser library uses bundled browser executables as part of its package to avoid
browser version conflicts and to enable browser patches to maximize automation possibilities. In practice
this means that some extra steps are required to install it for use in a project.

conda.yaml
------------------------------------------------------
Ensure you're using python 3.7 or newer.

Add ``nodejs``, ``robotframework-browser`` and ``rccPostInstall: rfbrowser init`` to ``conda.yaml``.

Example ``conda.yaml``:

.. code-block:: yaml

  channels:
    - conda-forge

  dependencies:
    - python=3.9.13
    - pip=22.1.2
    - nodejs=16.14.2
    - pip:
      - robotframework-browser==14.1.0
      - rpaframework==17.0.1
  rccPostInstall:
    - rfbrowser init

pip
---
See `upstream installation instructions`_

.. _upstream installation instructions: https://github.com/MarketSquare/robotframework-browser#installation-instructions

Keywords
========

🔗 Direct link to `keyword documentation <../../libdoc/RPA_Browser_Playwright.html>`_.

--------

.. raw:: html

   <iframe scrolling="no" id="libdoc" src="../../libdoc/RPA_Browser_Playwright.html"></iframe>
