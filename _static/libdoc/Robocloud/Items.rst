###################
Robot Framework API
###################

***********
Description
***********

:Library scope: Global

A library for interacting with RPA work items.

`WorkItems` is a collection of keywords for handling data
that is moved between different processes and Robot Framework
tasks. It allows storing and restoring values to/from cloud or file based
storage, and manipulating their contents.


Environment variables:

* RPA_WORKITEMS_ADAPTER: Import path to adapter, e.g. "mymodule.MyAdapter"
* RC_WORKSPACE_ID:       Current default workspace ID
* RC_WORKITEM_ID:        Current default work item ID

********
Keywords
********

:Clear Work Item:
  Remove all data in the current work item.

:Get Work Item Variable:
  :Arguments: name, default=None

  Return a single variable value from the work item,
  or default value if defined and key does not exist.
  If key does not exist and default is not defined, raises `KeyError`.


:Get Work Item Variables:
  Read all variables from the current work item and
  return them as a dictionary.

:Load Work Item:
  :Arguments: workspace_id, item_id

  Load work item for reading/writing.


:Load Work Item From Environment:
  Load current work item defined by the runtime environment.

  The corresponding environment variables are:

  * RC_WORKSPACE_ID
  * RC_WORKITEM_ID

:Save Work Item:
  Save the current data in the work item. If not saved,
  all changes are discarded when the library goes out of scope.

:Set Task Variables From Work Item:
  Convert all variables in the current work item to
  Robot Framework task variables.

:Set Work Item Variable:
  :Arguments: name, value

  Set a single variable value in the current work item.


:Set Work Item Variables:
  :Arguments: \*\*kwargs

  Set multiple variables in the current work item.

