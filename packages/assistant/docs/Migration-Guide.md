# Migration Guide

This is a guide for migrating from `RPA.Dialogs` to `RPA.Assistant`.

## Why RPA.Assistant?

We wanted to get rid of system dependencies like WebView. The new library
should work on systems that don't have any prerequisites installed, in order to
facilitate deployments of assistants on multiple machines.
We decided we should have a new library with a different name, because this
library will contain all the things Assistant related and will contain more
features than just those UI related.

## How to switch from Dialogs to Assistant

This section contains an exhaustive list of things that are no longer present
in the new library or have been changed. For new features, please check the
next section.

Firstly, you need to replace the dialogs library in your `conda.yaml` files
to `rpaframework-assistant` and all your imports from `RPA.Dialogs` to
`RPA.Assistant`.

Most of the Keywords and functions are the same, with some changes:

* syntax change for `Add file input` now the file_type has to be provided as
a comma-separated list of the extensions without any `*` or `.` like: `xls,xlsx`
* Date input is now just a simple text-type input that contains a date format validation
* For version 1.0 of the library, Date input only supports the ISO format `YYYY-MM-DD`
* Keyword `Add dialog next page button` was complety removed. Similar behaviour is now
possible with `Add Next Ui Button`
* Buttons from `Add submit buttons` are now visually separated from the rest of the interface
* Keyword `Run Dialog` no longer accepts the `clear` and `debug` arguments
* Keyword `Show dialog` was completly removed and async behaviour is only supported through callbacks
* Keywords `Wait dialog`, `Wait all dialogs`, `Close dialog` and `Close all dialogs` were completly removed

Besides this, the general look-and-feel of the UI and the components have changed.

## New features in Assistant

* Keyword `Run dialog` now has a `location` argument to position the main window
* New keyword `Ask User` that will behave similar to `Run Dialog` but it add by
default a submit and close buttons
* Inputs now support an additional `validation` argument that gives the option
to display error messages
* New keywords `Add Next Ui Button` and `Add button` that support a function
as callback when pressed
