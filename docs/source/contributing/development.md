# Development Guide

Here's what you need to know before adding or improving an existing library. But first,
let's see how they are usually intended to be used in order to understand how to
approach them.

_Python_
```python
from RPA.DocumentAI import DocumentAI

document_ai = DocumentAI()

def init_base64():
    document_ai.init_engine("base64ai", secret="<api-key>")
```

_Robot Framework_
```robotframework
*** Settings ***
Library     RPA.DocumentAI

*** Tasks ***
Init Base64
    Init Engine    base64ai    secret=<api-key>
```

As you can see in the examples above, the RF keyword `Init Engine` is actually the
`init_engine()` method of the instance of `DocumentAI` library class, which goes under
the same name as the module it comes from, _src/RPA/DocumentAI/DocumentAI.py_.

## Library class

Most of the libraries (if not all) we added in our
[rpaframework](https://pypi.org/project/rpaframework/) package follow the structure
you've seen above, where the library itself is either a  Python package or module
beginning with a capital letter, exposing a class having the same name & case.

- Every such class define methods which will be exposed as keywords in Robot Framework
  robots.
- A docstring should be present, explaining overall what the library does, and such
  documentation will be rendered and made visible on Robocorp's
  [docs](https://robocorp.com/docs/) page. (eg.
  [RPA.DocumentAI](https://robocorp.com/docs/libraries/rpa-framework/rpa-documentai))
- And some RF specific settings are usually added as class constants:
  ```python
  ROBOT_LIBRARY_SCOPE = "GLOBAL"
  ROBOT_LIBRARY_DOC_FORMAT = "REST"
  ```
- The `__init__` method definition is optional, but usually used to preserve the state
  of the library, like setting up a logger object and storing into variable members
  other instantiated dependencies objects or common data structures managed by the
  upcoming exposed methods as keywords.

## Library keywords (methods)

Now that you created your library class, start defining the methods that will bring the
library alive.

All the public methods (not prefixed with underscore `_`) are automatically exposed as
visible keywords intended to be used by the user taking advantage of RPA. They are
meant to simplify logic, abstract complexities and wrap other dependencies into simple
to use instructions making automation easier to grasp.

Imagine these as instructions you give to your robot in order to automate a task. They
should describe actions (as their name) which commands the robot. You configure them
and alter the default behavior with passed parameters where only the main inputs (eg.
a path to a file to process) should be mandatory and rest of the "options" should pose
a default commonly accepted behavior.

- Follow the Pythonic `snake_case` naming convention when you define methods.
- Ensure each such public method is
  [type annotated](https://docs.python.org/3/library/typing.html) and is well
  documented with a docstring following the
  [standard](https://github.com/robocorp/rpaframework/issues/357#issue-1100365552)
  format:
  - Summary describing what the keyword does.
  - Parameters description.
  - Python and Robot Framework usage examples.
- Ensure each method is low-coupled to the others and contain high-cohesive code
  blocks.
- While not necessary, you can make these stand out by using the `@keyword` decorator (
  imported with `from robot.api.deco import keyword`), place where you can configure
  a custom name for the expected keyword name (if the default is not satisfactory) and
  additional settings like `tags` and `types`.

## Library structure

Usually all these methods go into this single main library class, but sometimes you get
to write a lot of them and is not desirable to manage thousands of lines of code in a
single module. So you'd normally split the initial module into multiple such modules
which treat different topics and groups closely related methods into individual keyword
classes. Then you'd take all these "library parts" and unite them together into the
main library class.

Some good examples with slightly different approaches:
- Composition (has-a): [RPA.DocumentAI](../../../packages/main/src/RPA/DocumentAI/DocumentAI.py)
- Inheritance (is-a): [RPA.Desktop](../../../packages/main/src/RPA/Desktop/__init__.py)

So based on your needs, feel free to choose the simplest and most Pythonic one.

### Separate package
