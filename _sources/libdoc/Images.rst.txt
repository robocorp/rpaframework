###################
Robot Framework API
###################

***********
Description
***********

:Library scope: Task

Library for taking screenshots, matching templates, and
manipulating images.

********
Keywords
********

:Crop Image:
  :Arguments: image, region, filename=None, save_format=PNG

  Take a screenshot of the current desktop.


:Find Template In Image:
  :Arguments: image, template, region=None, limit=None, tolerance=None

  Attempt to find the template from the given image.

  :raises ImageNotFoundError: No match was found

:Find Template On Screen:
  :Arguments: template, \*\*kwargs

  Attempt to find the template image from the current desktop.
  For argument descriptions, see ``find_template_in_image()``

:Get Pixel Color In Image:
  :Arguments: image, point

  Get the RGB value of a pixel in the image.


:Get Pixel Color On Screen:
  :Arguments: point

  Get the RGB value of a pixel currently on screen.


:Show Region In Image:
  :Arguments: image, region, color=red, width=5

  Draw a rectangle onto the image around the given region.


:Show Region On Screen:
  :Arguments: region, color=red, width=5

  Draw a rectangle around the given region on the current desktop.


:Take Screenshot:
  :Arguments: filename=None, region=None, save_format=PNG

  Take a screenshot of the current desktop.


:Wait Template On Screen:
  :Arguments: template, timeout=5, \*\*kwargs

  Wait for template image to appear on current desktop.
  For further argument descriptions, see ``find_template_in_image()``

