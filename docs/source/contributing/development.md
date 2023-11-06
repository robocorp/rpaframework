# Development Guide

## Setup

Setup should be easy, as all our packages are isolated in their own _.venv_ maintained
by [Poetry](https://python-poetry.org/). To control such venvs, including the
_meta_ venv (which is the venv associated to the project bringing in all the packages
together), an [invocations](../../../invocations) set of helpers are used with the
`inv[oke]` command, based on the supported [tasks](../../../tasks.py). (file found in
every project)

So the first thing to run is `inv -l` to see a list of available commands, and if you
see just one, it means that you need to run `inv install-invocations` once, right
in the root directory of the repository. (the _meta_ project)

Explore our helper commands with `inv <cmd> --help` in order to learn more about each
one of them.

### Virtual environment(s)

In case [invoke](https://www.pyinvoke.org/) isn't installed yet on your system, you
have to do so by either your package manager or `pip install invoke` if you're fine
with relying on system's Python interpreter. Keep in mind that we recommend developing
with version **3.9.x** as that's what we recommend in our robots. So is better to
develop with the same version that is expected to be at the core of our robots. (pinned
in their _conda.yaml_)

For obtaining an env with such specific version, you can either use
[virtualenv](https://virtualenv.pypa.io/) or [pyenv](https://github.com/pyenv/pyenv),
but that's totally up to you.

#### Using `pyenv` on any platform to manage interpreters

With `pyenv`, I would do the following (in the repo root):
```console
% pyenv install 3.9.13
% pyenv local 3.9.13
```
and `pyenv versions` would display a nice confirmation given the locally set
interpreter:
```console
* 3.9.13 (set by /Users/cmin/Repos/rpaframework/.python-version)
```
and `pyenv which python`:
```console
/Users/cmin/.pyenv/versions/3.9.13/bin/python  # C:\Users\cmin\.pyenv\pyenv-win\versions\3.9.13\python.exe
```

#### Using system's interpreter on Windows (alternative to `pyenv`)

1. Uninstall any Python **3.9** version you might have on your system. Careful! This
   might break apps dependent on your system interpreter if this was previously taken
   into use.
2. [Download](https://www.python.org/downloads/) the latest Python **3.9** and make
   sure it will be available in `PATH` as well during installation.
3. Do NOT install nor create any `virtualenv` for this project, as Poetry manages its
   own virtual environments in separate _.venv_ directories for each package. Check the
   installed system-available interpreter version with:
   ```console
   > py -V
   Python 3.9.13
   ```

### Installing requirements

Now I'm good to go with running these installation commands once from the root dir:
```console
% python -m pip install -Ur invocations/requirements.txt
% inv install-invocations
```

Building the Poetry venv for the first time in the _main_ package:
```console
% cd packages/main
% inv install
```
and `poetry env info` would return me something like below:

###### On Mac

```console
Virtualenv
Python:         3.9.13
Implementation: CPython
Path:           /Users/cmin/Repos/rpaframework/packages/main/.venv
Executable:     /Users/cmin/Repos/rpaframework/packages/main/.venv/bin/python
Valid:          True

System
Platform:   darwin
OS:         posix
Python:     3.9.13
Path:       /Users/cmin/.pyenv/versions/3.9.13
Executable: /Users/cmin/.pyenv/versions/3.9.13/bin/python3.9
```

###### On Windows

```console
Virtualenv
Python:         3.9.13
Implementation: CPython
Path:           Z:\Repos\rpaframework\packages\main\.venv
Executable:     Z:\Repos\rpaframework\packages\main\.venv\Scripts\python.exe
Valid:          True

System
Platform:   win32
OS:         nt
Python:     3.9.13
Path:       C:\Users\cmin\.pyenv\pyenv-win\versions\3.9.13
Executable: C:\Users\cmin\.pyenv\pyenv-win\versions\3.9.13\python.exe
```

Meaning that my _.venv_ virtualenv dir managed by Poetry is in place and based on the
expected previously installed interpreter version.

### PyPI & DevPI

Before running any Poetry related `invoke` command, is desirable to configure it first
with the `inv install.setup-poetry` command, place where you can provide credentials
for configuring as well the servers into which you'll be publishing packages:
- PyPI: `inv install.setup-poetry -t <token>`
- DevPI: `inv install.setup-poetry -d https://devpi.robocorp.cloud/ci/test -u <usr> -p <pwd>`

Note that these secrets can be found in our shared [1Password](https://1password.com/)
store.

### IDE

I'm personally faster with PyCharm, but VSCode should be enough as well as long as you
can configure the following with ease:
- Switching between the Poetry *.venv*s based on the project you're developing. (so you
  use code completion and navigation from the env you're expecting to be active)
- Take advantage of `black`, `pylint`, `isort`, and even `mypy`, so you get your code
  auto-formatted. (an alias like `blackify='poetry run black src/RPA tests/python'` is
  sufficient for me)
- Run and debug examples right from the IDE's Terminal, Python Console and action
  buttons.

## Development

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

As you can see in the examples above, the **R**obot **F**ramework keyword `Init Engine`
is actually the `init_engine()` method of the instance of `DocumentAI` library class,
which goes under the same name as the module it comes from,
_src/RPA/DocumentAI/DocumentAI.py_.

### Library class

Most of the libraries (if not all) we added in our
[rpaframework](https://pypi.org/project/rpaframework/) package follow the structure
you've seen above, where the library itself is either a Python package or module
beginning with a capital letter, exposing a class having the same name & case.

- Every such class define methods which will be exposed as keywords in Robot Framework
  robots.
- A docstring should be present, explaining overall what the library does, and such
  documentation will be rendered and made visible on Robocorp's
  [docs](https://robocorp.com/docs/) page. (e.g.
  [RPA.DocumentAI](https://robocorp.com/docs/libraries/rpa-framework/rpa-documentai))
- And some RF specific settings are usually added as class constants:
  ```python
  ROBOT_LIBRARY_SCOPE = "GLOBAL"
  ROBOT_LIBRARY_DOC_FORMAT = "REST"
  ```
- The `__init__` method definition is optional, but usually used to preserve the state
  of the library, like setting up a logger object and storing into variable attributes
  other instantiated dependency objects or stateful common data structures managed by
  the upcoming exposed methods as keywords.

### Library keywords (methods)

Now that you created your library class, start defining the methods that will bring the
library alive.

All the public methods (not prefixed with underscore `_`) are automatically exposed as
visible keywords intended to be used by the user taking advantage of RPA. They are
meant to simplify logic, abstract complexities and wrap other dependencies into simple
to use instructions making automation easier to grasp.

Imagine these as instructions you give to your robot in order to automate a task. They
should describe actions (with their name) which commands the robot. You configure them
and alter the default behavior with passed parameters where only the main inputs (e.g.
a path to a file to process) should be mandatory, then the rest of the "options" should
pose a standard default behavior.

- Follow the Pythonic `snake_case` naming convention when you define methods.
- Ensure each such public method is
  [type annotated](https://docs.python.org/3/library/typing.html) and is well
  documented with a docstring following the
  [standard](https://github.com/robocorp/rpaframework/issues/357#issue-1100365552)
  format:
  - Summary describing what the keyword does.
  - Parameters description.
  - Python and Robot Framework usage examples.
- Ensure each method is [low-coupled](https://en.wikipedia.org/wiki/Coupling_(computer_programming))
  with the others and contains [high-cohesive](https://en.wikipedia.org/wiki/Cohesion_(computer_science))
  code blocks. ([learn more](https://stackoverflow.com/questions/14000762/what-does-low-in-coupling-and-high-in-cohesion-mean))
- Keep these principles in mind: **DRY**, **KISS**, **YAGNI**
  - [DRY, KISS & YAGNI Principles](https://henriquesd.medium.com/dry-kiss-yagni-principles-1ce09d9c601f)
  - [KISS, YAGNI, DRY – three principles that every developer should know about](https://www.boldare.com/blog/kiss-yagni-dry-principles/)
- While not necessary, you can make these stand out by using the `@keyword` decorator (
  imported with `from robot.api.deco import keyword`), place where you can configure
  a custom name for the expected keyword name (if the default is not satisfactory) and
  additional settings like `tags` and `types`.
  ```python
  @keyword
  def get_result(self, extended: bool = False) -> ResultType:
  ```
- Hiding keywords' logging due to security/privacy reasons can be achieved easily with
  the `RPA.Robocorp.utils.protect_keywords` utility.
  ```python
  protect_keywords("RPA.DocumentAI", ["init_engine"])
  ```

### Library structure

Usually all these methods go into this single library class, but sometimes you get
to write a lot of them and is not desirable to manage thousands of lines of code in a
single module. So you'd normally split the initial module into multiple such modules
which treat different topics, then groups closely related methods into individual
keyword classes. Then you'd take all these "library parts" and unite them together into
the initial library class.

You may choose from two design principles:
- Composition (has-a): [RPA.DocumentAI](../../../packages/main/src/RPA/DocumentAI/DocumentAI.py)
- Inheritance (is-a): [RPA.Desktop](../../../packages/main/src/RPA/Desktop/__init__.py)

#### Separate package (if needed)

Some libraries are too heavy on dependencies and the number of keywords to be
implemented directly into [main](../../../packages/main), therefore we create a new
package in this "monolith" repo, and we place them inside this one by following the
same structure. Afterwards this becomes self-contained and gets released as a separate
package into [PyPI](https://pypi.org/).

###### For internal developers

Based on the usage frequency (and reasonable set of dependencies it brings), such
package can be included in the _main_ one by pinning it into the
[pyproject.toml](../../../packages/main/pyproject.toml) file. If not, then for sure
this has to be pinned in the _meta_'s [pyproject.toml](../../../pyproject.toml) in
order to get the documentation built and test how all our packages will go along
together.

### Required changes

Is not easy to know by heart all the changes that need to be done when improving or
adding a new library, so here's a list with all the areas of interest:
- The library module/package itself discussed above.
- Updates into _pyproject.toml_:
  - Its newly required dependencies should be added with `poetry add <package>` command.
    (use the `-G dev` option if is a development one; e.g.: `poetry add requests@^2.28.1`)
    - The new packages will be visible in the project's _pyproject.toml_ file and a
      command like `inv install.update` will ensure a fresh _poetry.lock_ file
      after which the current _.venv_ is updated to.
    - Use `poetry update -vvv` if you want to see the output during the long runs that
      _meta_ building has.
  - Bump the `<major>.<minor>.<hotfix>` version number appropriately to reflect the
    type of change you introduced. (make sure you follow
    [semantic versioning](https://semver.org/))
    - The `inv build.version` can help you here with the bumping and a unique
      pre-release version management to avoid collision during testing.
      ([learn more](https://python-poetry.org/docs/cli/#version))
  - Update the [meta](../../../pyproject.toml) package as well to get a fresh
    _poetry.lock_ file if you're planning to release soon, right after the merge.
- The changes you've done should be summarized in a human-friendly way in the
  [release notes](../../../docs/source/releasenotes.rst). (read more in the
  [**Release**](#release-internal-developers-only) section).
- Adding a new library (additional requirements):
  - Ensure the new `RPA.<Library>` is now visible in the
    [README](../../../packages/main/README.rst) as well. (under **Libraries**)
  - There's a documentation entry under [libraries](../../../docs/source/libraries) as
    well. (follow the existing pattern)
  - Add exclusion rule in _invocations_' [_docs_](../../../invocations/docs.py)
    `EXCLUDE` list, so docs and libdocs get build correctly and only for what we intend
    to see. This is required when a library is split into multiple modules, therefore
    the docs generation process will include only the resources collated in the central
    package, so you won't run into duplicates given such a split.
  - Finally, a library entry should be added under our private **documentation** repo
    [config file](https://github.com/robocorp/documentation/blob/master/src/lib/libraries.ts).


### Linting & documentation

We mainly enforce `flake8` and `pylint` as automatically run linters when publishing to
production (PyPI), thing which you can independently run and check with
`inv code.lint`.

Use inline code comments like `# pylint: disable=<error>` or `# noqa: <code>` to ignore
those lines you want excluded from linting.

Docs should be built and displayed with the following commands from the _meta_ project:
```console
% inv install.update
% inv docs.build
% inv docs.host
```
Surf them on http://localhost:8000/. If they look right, you're ensured they'll be
displayed the same after merge.

## Testing

It's **very** important to cover your work with tests, at least the sweet scenario that
hits the core functionality, otherwise how can you be so confident that what you change
won't break already working stuff?

The risk of introducing [regressions](https://en.wikipedia.org/wiki/Software_regression)
is high, and unexpectedly appears even when you do a simple package upgrade, not even
talking about our own code/behaviour change. And tests will be your friend here, the
more covered you are with real-life scenarios, the faster you'll deliver value by
exchanging debugging and support time with tests development effort. (as you write them
once, but you're covered forever, on all platforms)

### Unit tests

These are inserted into the [python](../../../packages/main/tests/python) dir.
- Should be [atomic](https://testguild.com/atomic-tests/).
- Shouldn't rely on external resources. (patch the library and provide mocks)
  - [`pytest-mock`](https://pypi.org/project/pytest-mock/) (based on
    [`mock`](https://docs.python.org/3/library/unittest.mock.html))
  - [`monkeypatch`](https://docs.pytest.org/en/7.1.x/how-to/monkeypatch.html)

We write [pytest](https://pytest.org/) tests and usually run all of them with
`inv code.test-python`.

During development, for running a single test file, a command like below should suffice:
```console
% poetry run pytest -vv -s -o log_cli=true -o log_cli_level=DEBUG tests/python/test_documentai.py
```

But what if you want to run a single suite or just a single test from that suite?
```console
% poetry run pytest -vv -s -o log_cli=true -o log_cli_level=DEBUG tests/python/test_documentai.py::TestDocumentAI::test_switch_engine
```

### Robot tests

These are placed in the [robot](../../../packages/main/tests/robot) dir and are meant
to act like integration end-to-end tests. Therefore, we'll add test tasks testing the
affected keywords under a real scenario, even with a context built using other keywords
if necessary.

Imagine our customer using that affected keyword, how would he/she be calling it?
Sometimes, a quick win is to copy-paste the docstring's **RF** example, and this way,
you double-check that as well.

Robot tests are run with `inv code.test-robot` (excludes `skip` and `manual` tests),
this meaning collecting and running all of them from the package in focus.

Run all the tests in a robot test file (runs `skip`, excludes `manual`):
```console
% inv code.test-robot -r documentai
```

Run a single test in a robot test file (runs `skip` & `manual` as well):
```console
% inv code.test-robot -r documentai -t "Predict With Multiple Engines"
```

###### Skip tags

- `skip`: Tests that are usually skipped from CI, but they are still run on one's
  machine for extra coverage. (e.g. tests requiring a visible UI of the OS or tests
  accessing real external services requiring additional secrets setup and
  configuration)
- `manual`: Tests that are even harder to set up, because they require a scenario
  manually created by the developer, since the required dependencies can't be automated
  nor easily available to all developers. (e.g. testing Windows app automation over
  private or limited apps or under Windows 11 ARM emulated on a Mac M1 machine through
  Parallels)

### Resources & results

These tests may require [resources](../../../packages/main/tests/resources) (like input
files) and produce git-ignored [results](../../../packages/main/tests/results), which
are commonly used by both Python and Robot Framework tests.

### Development robot

Before implementing the tests, usually you want to quickly test/debug the library
through a test robot that maybe you don't want to commit. This robot already has the
context built through previously added boilerplate, thing which saves you time. (e.g.
some random [robots](https://github.com/cmin764/robots))

Or maybe you want to test the in-development behaviour through an existing Portal
[example](https://robocorp.com/portal/robot/robocorp/example-document-ai).

> The test robot can be either in Python or Robot Framework, it doesn't matter, as it
will use the very same logic from the library.

Therefore, you have two options:
1. Use a pre-release wheel built and pushed in our own test
   [DevPI](https://devpi.robocorp.cloud/ci/test).
   - Use `inv build.publish --ci` to build and publish the package into such DevPI URL.
   - Go to the URL above and copy the wheel direct link, then prefix it with
     our public read-only `<usr>:<pwd>@` credentials so the wheel is accessible for
     download now.
   - Paste such link into the _conda.yaml_ of the test robot, so the next time you
     rebuild the **holotree** env, it will use the code you just pushed, and you'll be
     able to test the new behaviour in a production-like scenario.
   - Such final test is important before hitting the "Merge" button, as you'll know for
     sure if the library will work as expected. (and that's the purpose of testing, to
     do it before merging the code)
2. Run the test robot with the package's virtual environment.
   - `cd` into the package you develop the changes into.
   - `poetry shell` to get a shell within the afferent Poetry _.venv_.
   - Now `cd` into the test robot directory and run it with:
     - `python -m robot -L TRACE -d ./output --task "<Task Name>" tasks.robot` if is a
       RF robot.
     - `python task.py` for a Python robot.
   - Getting such a shell will save you time from running commands with
     `poetry run python ...`, which would require to deal with longer paths.
   - Every new change brought in the project belonging to the active venv, will be
     **immediately reflected** in the next run of the testing robot. So you won't waste
     time with building and pushing test wheels on every change.

> In order to include more cross-dependent in-development packages under the same venv,
you have to use the `inv install.local` & `inv install.reset` helpers. (e.g.
introducing changes into **core**, which affects **windows**, which is included in
**main**, and you want to test how all these 3 work together)

### Manual breakpoints

If you want even more speed and variable/context inspection at the same time with the
development itself, you can either traditionally debug the project by running the
debugger or you can use hardcoded breakpoints. They will stop the execution and spawn a
Python shell for you to continue/inspect the code onwards. This shell can be exited
(and execution resumes) with `Ctrl+D`/`Ctrl+Z`.

You can place such "breakpoint" in either the library code itself, a Python
unit-test or a Python robot:
```python
from RPA.core.helpers import interact
interact(local={**globals(), **locals()})
```

## Release (internal developers only)

Once your PR passed the CI and all your manual tests, including a pre-release wheel
sample run either locally or through Control Room with a custom/default Worker, you
should be confident enough to hit the "Merge" button.

Post-merge, you'd normally switch back to the _master_ branch, pull in all the just
merged changes (optionally remove your local merged branch as you don't need it
anymore) and finally publish the package with `inv build.publish`. Note that this will
publish in the official PyPI (and not DevPI as happening with the `--ci` flag).

### Prerequisites

A few things to take care first, right before publishing the package for real:
- Previously released sub-package (e.g. `rpaframework-windows`) got bumped as well
  under the _main_'s _pyproject.toml_ pin. (if you intend to set this as a minimum
  version)
  - If the released package is not part of _main_ then maybe it is included in _meta_,
    therefore make sure you update the version there as well, so it makes it to the
    docs.
- You run `inv install.update` for both _main_ and _meta_.
- There's a release note summarizing the change(s) about to be released.
  - The **Upcoming** release notes (if any) are moved under the **Released** section
    altogether. (since you're releasing everything that was pushed so far)
  - Independent packages from _main_ can be announced the same, but without a version
    number since there's no ``rpaframework`` package holding them. (only _meta_ & docs)
- Your Poetry setup is configured accordingly for PyPI push. (see [**Setup**](#setup))

###### Release notes formatting

While we don't have automatic linting for release notes yet, here is some common sense
to follow:
- Restructured Text format requires one blank line before any bullet-point block,
  otherwise the rendering won't happen as expected.
- **Libraries** are bold (so version numbers), while `Key Words` are code-like (so
  library package names). Parameters, arguments and file_names.ext are usually
  _italic_.
- **88** chars limit per line. (we can increase it ofc, but for now this aligns with
  our linters) -- rule can be broken with longer URLs
- Specifying ```:issue:`<nr>` ``` and ```:pr:`<nr>` ``` where possible.
- One blank line for normal spacing, two blank lines for top-level titles: **Upcoming**
  and **Released**.
- `DD MMM YYYY` date format, prefixed by the library version if it includes a release
  of `rpaframework` as well. (as independent packages aren't included by default in the
  _main_ library)
- Breaking changes go under the ⚠️ `.. warning::` directive block.
- Two spaces (no tabs) for indentation. (don’t mix 4s with 2s, keep it consistent)
- Sentences usually start with a capital letter and end with punctuation.
- Try to correct your English with [Grammarly](https://www.grammarly.com/).

### Post-publish

Now that your package was published successfully and visible in
[PyPI](https://pypi.org/), the work isn't done. There's docs and announcements.

1. Our [docs site](https://robocorp.com/docs/) should be reflecting the latest built
   and pushed documentation (that's why we updated the _meta_ package). They are
   visible in our legacy rpaframework.org site first (which you can check initially for
   problems). But for making them visible in the official docs site as well, you should
   trigger the following documentation
   [workflow](https://github.com/robocorp/documentation/actions/workflows/manual-build.yml).
2. Release notes can be copy-pasted from the freshly built
   [rpaframework.org](https://rpaframework.org/releasenotes.html) page into a new
   release managed by [releasenotes.io](https://app.releasenotes.io/dashboard).
   1. The same message goes into our Slack announcement channels: `#rpaframework`
      (internal) & `#announcements` (community).
   2. Make sure to hyperlink the version number of the announcement message with the
      release URL obtained at [Robocorp updates](https://updates.robocorp.com/) after
      officially publishing it.

🙏 Don't get intimidated by the extensive details presented here, as they will come
naturally after your first contribution to the library. Wishing you an amazing time
committing and promoting your value through our library!
