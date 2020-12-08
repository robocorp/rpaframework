.. _playwright:

##################
Browser.Playwright
##################


New Playwright based browser automation library. Upstream examples, 
docs and issue tracker available at `github.`_

.. _github.: https://github.com/marketsquare/robotframework-browser#robotframework-browser

Install instructions
====================

The playwright based browser library uses bundled browser executables as part of it's package to avoid
browser version conflicts and enable browser patches to maximize automation possibilities. In practice
this means that some extra steps are required to install it for use in a project.

conda.yaml (RCC, VSCode and Robocorp Lab)
=========================================
Ensure you're using python 3.7 or newer.

Add nodejs, robotframework-browser and rccPostInstall: rfbrowser init to conda.yaml

Example conda.yaml:

.. code-block:: yaml

  channels:
    - defaults
    - conda-forge
  dependencies:
    - python=3.7.5
    - pip=20.1
    - nodejs=14.2.0
    - pip:
      - rpaframework==6.7.1
      - robotframework-browser==2.3.3
  rccPostInstall:
    - rfbrowser init

pip
====================
See `upstream installation instructions`_

.. _upstream installation instructions: https://github.com/MarketSquare/robotframework-browser#installation-instructions


.. toctree::
   :maxdepth: 1
   :hidden:

   python

Keywords
========

🔗 Direct link to `keyword documentation <../../libdoc/RPA_Browser_Playwright.html>`_.

--------

.. raw:: html

   <iframe scrolling="no" class="libdoc" src="../../libdoc/RPA_Browser_Playwright.html" />
