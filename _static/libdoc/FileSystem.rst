###################
Robot Framework API
###################

***********
Description
***********

:Library scope: Task

`FileSystem` is a library for finding, creating, and modifying
files on a local filesystem.

********
Keywords
********

:Append To Binary File:
  :Arguments: path, content

  Appends binary content to the given file.


:Append To File:
  :Arguments: path, content, encoding=utf-8

  Appends text to the given file.


:Change File Extension:
  :Arguments: path, extension

  Replaces file extension for file at given path.


:Copy Directory:
  :Arguments: source, destination

  Copy directory from source path to destination path.


:Copy File:
  :Arguments: source, destination

  Copy a file from source path to destination path.


:Copy Files:
  :Arguments: sources, destination

  Copy multiple files to destination folder.


:Create Binary File:
  :Arguments: path, content=None

  Creates a new binary file, and writes content if any is given.


:Create Directory:
  :Arguments: path, parents=False

  Creates a directory and (optionally) non-existing parent directories.


:Create File:
  :Arguments: path, content=None, encoding=utf-8

  Creates a new text file, and writes content if any is given.


:Does Directory Exist:
  :Arguments: path

  Returns True if given directory exists, False if not.


:Does Directory Not Exist:
  :Arguments: path

  Return True if directory does not exist, False if it does.


:Does File Exist:
  :Arguments: path

  Returns True if given file exists, False if not.


:Does File Not Exist:
  :Arguments: path

  Returns True if file does not exist, False if it does.


:Empty Directory:
  :Arguments: path

  Removes all files in the given directory.


:Find Files:
  :Arguments: pattern, include_dirs=True, include_files=True

  Find files recursively according to pattern.


:Get File Creation Date:
  :Arguments: path

  Returns the creation time in seconds.
  Note: Linux sets this whenever file metadata changes


:Get File Extension:
  :Arguments: path

  Returns the suffix for the file.


:Get File Modified Date:
  :Arguments: path

  Returns the modified time in seconds.


:Get File Name:
  :Arguments: path

  Returns only the filename portion of a path.


:Get File Size:
  :Arguments: path

  Returns the file size in bytes.


:Is Directory Empty:
  :Arguments: path=None

  Returns True if the given directory has no files or subdirectories.


:Is Directory Not Empty:
  :Arguments: path=None

  Returns True if the given directory has any files or subdirectories.


:Is File Empty:
  :Arguments: path

  Returns True if the given file has no content, i.e. has zero size.


:Is File Not Empty:
  :Arguments: path

  Returns True if the given file has content, i.e. larger than zero size.


:Join Path:
  :Arguments: \*parts

  Joins multiple parts of a path together.


:List Directories In Directory:
  :Arguments: path=None

  Lists all directories in the given directory, relative to it.


:List Files In Directory:
  :Arguments: path=None

  Lists all files in the given directory, relative to it.


:Log Directory Tree:
  :Arguments: path=None

  Logs all of the files in the directory recursively.


:Move Directory:
  :Arguments: source, destination, overwrite=False

  Move directory from source path to destination path.


:Move File:
  :Arguments: source, destination, overwrite=False

  Move file from source path to destination path,
  optionally overwriting the destination.


:Move Files:
  :Arguments: sources, destination, overwrite=False

  Move multiple files to the destination folder.


:Normalize Path:
  :Arguments: path

  Converts to absolute path and resolves any symlinks.


:Read Binary File:
  :Arguments: path

  Reads a file in binary mode and returns the content.
  Does not attempt to decode the content in any way.


:Read File:
  :Arguments: path, encoding=utf-8

  Reads a file as text, with given `encoding`, and returns the content."


:Remove Directory:
  :Arguments: path, recursive=False

  Returns the given directory, and optionally everything it contains.


:Remove File:
  :Arguments: path

  Removes the given file.


:Remove Files:
  :Arguments: \*paths

  Removes multiple files.


:Run Keyword If File Exists:
  :Arguments: path, keyword, \*args

  If file exists at `path`, execute given keyword with arguments.

  **Example**

  .. code:: robotframework

      Run keyword if file exists    orders.xlsx    Process orders


:Touch File:
  :Arguments: path

  Creates a file with no content, or if file already exists,
  updates the modification and access times.


:Wait Until Created:
  :Arguments: path, timeout=5.0

  Poll path until it exists, or raise exception if timeout
  is reached.


:Wait Until Modified:
  :Arguments: path, timeout=5.0

  Poll path until it has been modified after the keyword was called,
  or raise exception if timeout is reached.


:Wait Until Removed:
  :Arguments: path, timeout=5.0

  Poll path until it doesn't exist, or raise exception if timeout
  is reached.

