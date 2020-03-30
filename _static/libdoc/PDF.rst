###################
Robot Framework API
###################

***********
Description
***********

:Library scope: Task

RPA Framework library for PDF management.


********
Keywords
********

:Accept Page Break:
  Accept automatic page break or not

:Add Font:
  :Arguments: family, style=, fname=, uni=False

  Add a TrueType or Type1 font

:Add Link:
  Create a new internal link

:Add Page:
  :Arguments: orientation=

  Start a new page

:Add Pages:
  :Arguments: pages=1

  Adds pages into PDF documents


:Alias Nb Pages:
  :Arguments: alias={nb}

  Define an alias for total number of pages

:Cell:
  :Arguments: \*args, \*\*kwargs

  Output a cell

:Check Page:
  Decorator to protect drawing methods

:Close:
  Terminate document

:Code 39:
  :Arguments: \*args, \*\*kwargs

  Barcode 3of9

:Dashed Line:
  :Arguments: \*args, \*\*kwargs

  Draw a dashed line. Same interface as line() except:
  - dash_length: Length of the dash
  - space_length: Length of the space between dashes

:Ellipse:
  :Arguments: \*args, \*\*kwargs

  Draw a ellipse

:Error:
  :Arguments: msg

  Fatal error

:Footer:
  Footer to be implemented in your own inherited class

:Get String Width:
  :Arguments: s

  Get width of a string in the current font

:Get X:
  Get x position

:Get Y:
  Get y position

:Header:
  Header to be implemented in your own inherited class

:Image:
  :Arguments: \*args, \*\*kwargs

  Put an image on the page

:Interleaved 2 Of 5:
  :Arguments: \*args, \*\*kwargs

  Barcode I2of5 (numeric), adds a 0 if odd lenght

:Line:
  :Arguments: \*args, \*\*kwargs

  Draw a line

:Link:
  :Arguments: x, y, w, h, link

  Put a link on the page

:Ln:
  :Arguments: \*args, \*\*kwargs

  Line Feed; default value is last cell height

:Multi Cell:
  :Arguments: \*args, \*\*kwargs

  Output text with automatic or explicit line breaks

:Normalize Text:
  :Arguments: txt

  Check that text input is in the correct format/encoding

:Open:
  Begin document

:Output:
  :Arguments: name=, dest=

  Output PDF to some destination

:Page No:
  Get current page number

:Rect:
  :Arguments: \*args, \*\*kwargs

  Draw a rectangle

:Rotate:
  :Arguments: \*args, \*\*kwargs



:Set Author:
  :Arguments: author

  Author of document

:Set Auto Page Break:
  :Arguments: auto, margin=0

  Set auto page break mode and triggering margin

:Set Compression:
  :Arguments: compress

  Set page compression

:Set Creator:
  :Arguments: creator

  Creator of document

:Set Display Mode:
  :Arguments: zoom, layout=continuous

  Set display mode in viewer

  The "zoom" argument may be 'fullpage', 'fullwidth', 'real',
  'default', or a number, interpreted as a percentage.

:Set Draw Color:
  :Arguments: r, g=-1, b=-1

  Set color for all stroking operations

:Set Fill Color:
  :Arguments: r, g=-1, b=-1

  Set color for all filling operations

:Set Font:
  :Arguments: family, style=, size=0

  Select a font; size given in points

:Set Font Size:
  :Arguments: size

  Set font size in points

:Set Keywords:
  :Arguments: keywords

  Keywords of document

:Set Left Margin:
  :Arguments: margin

  Set left margin

:Set Line Width:
  :Arguments: width

  Set line width

:Set Link:
  :Arguments: link, y=0, page=-1

  Set destination of internal link

:Set Margins:
  :Arguments: left, top, right=-1

  Set left, top and right margins

:Set Right Margin:
  :Arguments: margin

  Set right margin

:Set Subject:
  :Arguments: subject

  Subject of document

:Set Text Color:
  :Arguments: r, g=-1, b=-1

  Set color for text

:Set Title:
  :Arguments: title

  Title of document

:Set Top Margin:
  :Arguments: margin

  Set top margin

:Set X:
  :Arguments: x

  Set x position

:Set Xy:
  :Arguments: x, y

  Set x and y positions

:Set Y:
  :Arguments: y

  Set y position and reset x

:Template Html To Pdf:
  :Arguments: template, filename, variables=None

  Use HTML template file to generate PDF file.


:Text:
  :Arguments: \*args, \*\*kwargs

  Output a string

:Write:
  :Arguments: \*args, \*\*kwargs

  Output text in flowing mode

:Write Html:
  :Arguments: text, image_map=None

  Parse HTML and convert it to PDF
