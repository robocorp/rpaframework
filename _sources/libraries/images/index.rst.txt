######
Images
######

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`Images` is a library for taking screenshots, matching templates, and
generally manipulating images. It can also be used for GUI-based automation
when traditional UI locators are not available.

Coordinates
===========

The coordinates used in the library are pairs of x and y values that
represent pixels. The upper left corner of the image or screen
is (0, 0). The x-coordinate increases towards the right, and the y-coordinate
increases towards the bottom.

Regions are represented as tuples of (left, top, right, bottom). For example,
a 400 by 200-pixel region in the upper left corner would be (0, 0, 400, 200).

Template matching
=================

Template matching refers to an operation where the (potential) location of
a smaller image is searched from a larger image. It can be used for verifying
certain conditions or locating UI elements for desktop or web automation.

.. note::
   Currently creating templates requires an external tool
   like Windows' `Snipping Tool`.

Requirements
============

The default installation depends on `Pillow <https://python-pillow.org/>`_
library, which is used for general image manipulation operations.

For more robust and faster template matching, the library can use a combination
of `NumPy <https://numpy.org/>`_ and `OpenCV <https://opencv.org/>`_.
They can be installed by opting in to the `cv` dependency:

``pip install rpaframework[cv]``

********
Examples
********

Robot Framework
===============

The `Images` library can be imported and used directly in Robot Framework,
for instance, for capturing screenshots or verifying something on the screen.

Desktop automation based on images should be done using the corresponding
desktop library, e.g., :ref:`library-desktop-windows`.

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library    RPA.Images

    *** Keywords ***
    Should show success
        [Documentation]    Raises ImageNotFoundError if success image is not on screen
        Find template on screen    ${CURDIR}${/}success.png

    Save screenshot to results
        [Documentation]    Saves screenshot of desktop with unique name
        ${timestamp}=      Get current date    result_format=%H%M%S
        Take screenshot    filename=${OUTPUT_DIR}${/}desktop_${timestamp}.png

Python
======

.. code-block:: python
    :linenos:

    from RPA.Images import Images

    def draw_matches_on_desktop(template):
        lib = Images()
        screenshot = lib.take_screenshot()

        matches = lib.find_template_in_image(screenshot, template)
        for match in matches:
            lib.show_region_in_image(screenshot, match)

        screenshot.save("matches.png")

*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../robot/Images.rst
   python
