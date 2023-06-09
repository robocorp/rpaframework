import glob
import logging
import os
import platform
import subprocess
from datetime import date
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import flet
from flet import (
    AppBar,
    Checkbox,
    Column,
    Container,
    Control,
    Dropdown,
    ElevatedButton,
    FilePicker,
    FilePickerResultEvent,
    Image,
    MainAxisAlignment,
    Markdown,
    Radio,
    RadioGroup,
    Row,
    Slider,
    Text,
    TextField,
    alignment,
    colors,
    icons,
)
from flet_core import Stack
from flet_core.control_event import ControlEvent
from flet_core.dropdown import Option
from robot.api.deco import keyword, library
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
from robot.utils.dotdict import DotDict
from typing_extensions import Literal
from RPA.Assistant.callback_runner import CallbackRunner

from RPA.Assistant.flet_client import FletClient
from RPA.Assistant.types import (
    Icon,
    LayoutError,
    Location,
    Options,
    Result,
    Size,
    VerticalLocation,
    WindowLocation,
)
from RPA.Assistant.utils import location_to_absolute, optional_str, to_options


@library(scope="GLOBAL", doc_format="REST", auto_keywords=False)
class Assistant:
    """The `Assistant` library provides a way to display information to a user
    and request input while a robot is running. It allows building processes
    that require human interaction. Also it offers capabilities of running
    other robots inside the current one and determine what to display to the
    user based on his previous responses.

    It is not included in the `rpaframework` package, so in order to use it
    you have to add `rpaframework-assistant` with the desired version in your
    *conda.yaml* file

    Some examples of use-cases could be the following:

    - Displaying generated files after an execution is finished
    - Displaying dynamic and user-friendly error messages
    - Requesting passwords or other personal information
    - Running Keywords based on user's actions
    - Displaying dynamic content based on user's actions
    - Automating based on files created by the user

    **Workflow**

    The library is used to create dialogs, i.e. windows, that can be composed
    on-the-fly based on the current state of the execution.

    The content of the dialog is defined by calling relevant keywords
    such as ``Add text`` or ``Add file input``. When the dialog is opened
    the content is generated based on the previous keywords.

    Depending on the way the dialog is started, the execution will either
    block or continue while the dialog is open. During this time the user
    can freely edit any possible input fields or handle other tasks.

    After the user has successfully submitted the dialog, any possible
    entered input will be returned as a result. The user also has the option
    to abort by closing the dialog window forcefully.

    **Results**

    Each input field has a required ``name`` argument that controls what
    the value will be called in the result object. Each input name should be
    unique, and must not be called ``submit`` as that is reserved for the submit
    button value.

    A result object is a Robot Framework DotDict, where each key
    is the name of the input field and the value is what the user entered.
    The data type of each field depends on the input. For instance,
    a text input will have a string, a checkbox will have a boolean, and
    a file input will have a list of paths.

    If the user closed the window before submitting or there was an internal
    error, the results object returned by Run Dialog or Ask User won't have a "submit"
    key.

    **Layouting**

    By default elements are added to the assistant dialog from top to bottom, with a bit
    of margin around each element to add spaciousness. This margin is added as a
    ``Container`` you can manually use ``Open Container`` to override the default
    container. You can use it to set smaller margins.

    You can combine layouting elements with each other. Layouting elements need to be
    closed with the corresponding ``Close`` keyword. (So ``Open Row`` and then
    ``Close Row``.)

    ``Open Row`` can be used to layout elements in the same row.

    ``Open Column`` can be used to layout elements in columns.

    ``Open Stack`` and multiple ``Open Container``'s inside it can be used to set
    positions like Center, Topleft, BottomRight, or coordinate tuples likes (0, 0),
    (100, 100) and such.

    ``Open Container`` can bse used for absolute positioning inside a Stack, or anywhere
    for setting background color or margins and paddings.

    ``Open Navbar`` can be used to make a navigation bar that will stay at the top of
    the dialog. Its contents won't be cleared when.


    **Examples**

    .. code-block:: robotframework

        Success dialog
            Add icon      Success
            Add heading   Your orders have been processed
            Add files     *.txt
            Run dialog    title=Success

        Failure dialog
            Add icon      Failure
            Add heading   There was an error
            Add text      The assistant failed to login to the Enterprise portal
            Add link      https://robocorp.com/docs    label=Troubleshooting guide
            Run dialog    title=Failure

        Large dialog
            Add heading    A real chonker   size=large
            Add image      fat-cat.jpeg
            Run dialog     title=Large    height=1024    width=1024

        Confirmation dialog
            Add icon      Warning
            Add heading   Delete user ${username}?
            Add submit buttons    buttons=No,Yes    default=Yes
            ${result}=    Run dialog
            IF   $result.submit == "Yes"
                Delete user    ${username}
            END

        Input form dialog
            Add heading       Send feedback
            Add text input    email    label=E-mail address
            Add text input    message
            ...    label=Feedback
            ...    placeholder=Enter feedback here
            ...    maximum_rows=5
            ${result}=    Run dialog
            Send feedback message    ${result.email}  ${result.message}
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        os.environ["FLET_LOG_LEVEL"] = "warning"
        self._client = FletClient()
        self._callbacks = CallbackRunner(self._client)
        self._required_fields: Set[str] = set()
        self._open_layouting: List[str] = []

        try:
            # Prevent logging from keywords that return results
            keywords = [
                "Run dialog",
                "Ask user",
            ]
            BuiltIn().import_library(
                "RPA.core.logger.RobotLogListener", "WITH NAME", "RPA.RobotLogListener"
            )
            listener = BuiltIn().get_library_instance("RPA.RobotLogListener")
            # useful to comment out when debugging
            listener.register_protected_keywords(keywords)
        except RobotNotRunningError:
            pass

    def _create_closing_button(self, label="Submit") -> Control:
        def validate_and_close(*_):
            # remove None's from the result dictionary
            for field_name in list(self._client.results.keys()):
                if self._client.results[field_name] is None:
                    self._client.results.pop(field_name)

            should_close = True

            for field_name in self._required_fields:
                value = self._client.results.get(field_name)
                error_message = (
                    None if value else f"Mandatory field {field_name} was not completed"
                )
                if error_message:
                    should_close = False
                    self._client.set_error(field_name, error_message)
                    self._client.flet_update()

            for field_name, error in self._callbacks.validation_errors.items():
                if error is not None:
                    should_close = False
                    self._client.set_error(field_name, error)
            self._client.flet_update()

            if should_close:
                self._client.results["submit"] = label
                self._client.page.window_destroy()

        return ElevatedButton(label, on_click=validate_and_close)

    @keyword(tags=["dialog", "running"])
    def clear_dialog(self) -> None:
        """Clear dialog and results while it is running."""
        self._client.results = {}
        self._client.clear_elements()

    @keyword
    def add_heading(
        self,
        heading: str,
        size: Size = Size.Medium,
    ) -> None:
        """Add a centered heading text element

        :param heading: The text content for the heading
        :param size:    The size of the heading

        Supported ``size`` values are Small, Medium, and Large. By default uses
        the value Medium.

        Example:

        .. code-block:: robotframework

            Add heading     User information  size=Large
            Add heading     Location          size=Small
            Add text input  address           label=User address
            Run dialog
        """
        if not isinstance(size, Size):
            size = Size(size)

        size_dict = {
            Size.Small: "headlineSmall",
            Size.Medium: "headlineMedium",
            Size.Large: "headlineLarge",
        }

        self._client.add_element(element=Text(heading, style=size_dict[size]))

    @keyword
    def add_text(
        self,
        text: str,
        size: Size = Size.Medium,
    ) -> None:
        """Add a text paragraph element, for larger bodies of text

        :param text: The text content for the paragraph
        :param size: The size of the text

        Supported ``size`` values are Small, Medium, and Large. By default uses
        the value Medium.

        Example:

        .. code-block:: robotframework

            Add heading   An error occurred
            Add text      There was an error while requesting user information
            Add text      ${error}   size=Small
            Run dialog
        """
        if not isinstance(size, Size):
            size = Size(size)

        if size == Size.Small:
            self._client.add_element(element=Text(text, style="bodySmall"))
        elif size == Size.Medium:
            self._client.add_element(element=Text(text, style="bodyMedium"))
        elif size == Size.Large:
            self._client.add_element(element=Text(text, style="bodyLarge"))

    @keyword
    def add_link(
        self,
        url: str,
        label: Optional[str] = None,
    ) -> None:
        """Add an external URL link element

        :param url:   The URL for the link
        :param label: A custom label text for the link

        Adds a clickable link element, which opens the user's default
        browser to the given ``url``. Optionally a ``label`` can be given
        which is shown as the link text, instead of the raw URL.

        Example:

        .. code-block:: robotframework

            Add heading    An error occurred
            Add text       See link for documentation
            Add link       https://robocorp.com/docs    label=Troubleshooting
            Run dialog
        """
        if not label:
            label = url
        self._client.add_element(
            Markdown(
                f"[{label}]({url})",
                on_tap_link=lambda e: self._client.page.launch_url(e.data),
            )
        )

    @keyword
    def add_image(
        self,
        url_or_path: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> None:
        """Add an image element, from a local file or remote URL

        :param url_or_path: The location of the image
        :param width:       The static width of the image, in pixels
        :param height:      The static height of the image, in pixels

        Adds an inline image to the dialog, which can either
        point to a local file path on the executing machine or to
        a remote URL.

        By default the image is resized to fit the width of the dialog
        window, but the width and/or height can be explicitly defined
        to a custom value. If only one of the dimensions is given,
        the other is automatically changed to maintain the correct aspect ratio.

        Example:

        .. code-block:: robotframework

            Add image      company-logo.png
            Add heading    To start, please press the Continue button   size=Small
            Add submit buttons    Continue
            Run dialog
        """

        self._client.add_element(
            Container(content=Image(src=url_or_path, width=width, height=height))
        )

    @keyword
    def add_file(
        self,
        path: str,
        label: Optional[str] = None,
    ) -> None:
        """Add a file element, which links to a local file

        :param path:  The path to the file
        :param label: A custom label text for the file

        Adds a button which opens a local file with the corresponding
        default application. Can be used for instance to display generated
        files from the robot to the end-user.

        Optionally a custom ``label`` can be given for the button text.
        By default uses the filename of the linked file.

        Example:

        .. code-block:: robotframework

            ${path}=   Generate order files
            Add heading    Current orders
            Add file    ${path}    label=Current
            Run dialog
        """
        resolved = Path(path).resolve()
        self.logger.info("Adding file: %s", resolved)

        if not resolved.exists():
            self.logger.warning("File does not exist: %s", resolved)

        def open_file(*_):
            if platform.system() == "Windows":
                os.startfile(resolved)  # type: ignore # pylint: disable=no-member
            elif platform.system() == "Darwin":
                subprocess.call(["open", resolved])
            else:
                subprocess.call(["xdg-open", resolved])

        self._client.add_element(
            element=ElevatedButton(
                text=(label or str(resolved)), icon=icons.FILE_OPEN, on_click=open_file
            )
        )

    @keyword
    def add_files(
        self,
        pattern: str,
    ) -> None:
        """Add multiple file elements according to the given file pattern

        :param pattern: File matching pattern

        See the keyword ``Add file`` for information about the inserted
        element itself.

        The keyword uses Unix-style glob patterns for finding matching files,
        and the supported pattern expressions are as follow:

        ========== ================================================
        Pattern    Meaning
        ========== ================================================
        ``*``      Match everything
        ``?``      Match any single character
        ``[seq]``  Match any character in seq
        ``[!seq]`` Match any character not in seq
        ``**``     Match all files, directories, and subdirectories
        ========== ================================================

        If a filename has any of these special characters, they
        can be escaped by wrapping them with square brackets.

        Example:

        .. code-block:: robotframework

            # Add all excel files
            Add files    *.xlsx

            # Add all log files in any subdirectory
            Add files    **/*.log

            # Add all PDFs between order0 and order9
            Add files    order[0-9].pdf
        """
        matches = glob.glob(pattern, recursive=True)
        for match in sorted(matches):
            self.add_file(match)

    @keyword
    def add_icon(self, variant: Icon, size: int = 48) -> None:
        """Add an icon element from RPA.Assistant's short icon list.

        :param variant: The icon type
        :param size:    The size of the icon

        Adds an icon which can be used to indicate status
        or the type of dialog being presented.

        The currently supported icon types are:

        ======= ==========================
        Name    Description
        ======= ==========================
        Success A green check mark
        Warning An orange warning triangle
        Failure A red cross or X mark
        ======= ==========================

        The ``size`` of the icon can also be changed,
        to a given height/width of pixels.

        Example:

        .. code-block:: robotframework

            Add icon              Warning    size=64
            Add heading           Do you want to delete this order?
            Add submit buttons    buttons=No,Yes
            ${result}=    Run dialog
        """
        if not isinstance(variant, Icon):
            variant = Icon(variant)

        flet_icon_conversions: Dict[Icon, Tuple[str, str]] = {
            Icon.Success: (icons.CHECK, colors.GREEN_500),
            Icon.Warning: (icons.WARNING, colors.YELLOW_500),
            Icon.Failure: (icons.CLOSE, colors.RED_500),
        }
        flet_icon, color = flet_icon_conversions[variant]

        self._client.add_element(flet.Icon(name=flet_icon, color=color, size=size))

    @keyword
    def add_flet_icon(
        self,
        icon: str,
        color: Optional[str] = None,
        size: Optional[int] = 24,
    ):
        """Add an icon from a large gallery of icons.

        :param icon:      Corresponding flet icon name. Check
                          https://gallery.flet.dev/icons-browser/ for a list of icons.
                          Write the name in ``lower_case``
        :param color:     Color for the icon. Default depends on icon. Allowed values
                          are colors from
                          https://github.com/flet-dev/flet/blob/035b00104f782498d084c2fd7ee96132a542ab7f/sdk/python/packages/flet-core/src/flet_core/colors.py#L37
                          or ARGB/RGB (#FFXXYYZZ or #XXYYZZ).
        :param size:      Integer size for the icon.


        Example:

        .. code-block:: robotframework

            Add Heading    Check icon
            Add Flet Icon  icon_name=check_circle_rounded  color=FF00FF  size=48
            Run Dialog
        """
        self._client.add_element(flet.Icon(name=icon, color=color, size=size))

    @keyword(tags=["input"])
    def add_text_input(
        self,
        name: str,
        label: Optional[str] = None,
        placeholder: Optional[str] = None,
        validation: Optional[Union[Callable, str]] = None,
        default: Optional[str] = None,
        required: bool = False,
        minimum_rows: Optional[int] = None,
        maximum_rows: Optional[int] = None,
    ) -> None:
        """Add a text input element

        :param name:        Name of result field
        :param label:       Label for field
        :param placeholder: Placeholder text in input field
        :param validation:   Validation function for the input field
        :param default:     Default value if the field wasn't completed
        :param required:    If true, will display an error if not completed
        :param minimum_rows: Minimum number of rows to display for the input field
        :param maximum_rows: Maximum number of rows to display for the input field, the
                             input content can be longer but a scrollbar will appear

        Adds a text field that can be filled by the user. The entered
        content will be available in the ``name`` field of the result.

        For customizing the look of the input, the ``label`` text can be given
        to add a descriptive label and the ``placholder`` text can be given
        to act as an example of the input value.

        The `default` value will be assigned to the input field if the user
        doesn't complete it. If provided, the placeholder won't be shown.
        This is `None` by default. Also, if a default value is provided
        and the user deletes it, `None` will be the corresponding value in
        the results dictionary.

        Example:

        .. code-block:: robotframework

            Add heading    Send feedback
            Add text input    email    label=E-mail address
            Add text input    message
            ...    label=Feedback
            ...    placeholder=Enter feedback here
            ${result}=    Run dialog
            Send feedback message    ${result.email}  ${result.message}

        Validation example:

        .. code-block:: robotframework

            Validate Email
                [Arguments]    ${email}
                # E-mail specification is complicated, this matches that the e-mail has
                # at least one character before and after the @ sign, and at least one
                # character after the dot.
                ${regex}=    Set Variable    ^.+@.+\\..+
                ${valid}=    Run Keyword And Return Status    Should Match Regexp  ${email}  ${regex}
                IF  not $valid
                    RETURN  Invalid email address
                END

            Open Dialog
                Add heading    Send feedback
                Add text input    email
                ...    label=Email
                ...    validation=Validate Email
                ${result}=    Run dialog
                Log  ${result.email}

        .. code-block:: python

            import re
            def validate_email(email):
                # E-mail specification is complicated, this matches that the e-mail has
                # at least one character before and after the @ sign, and at least one
                # character after the dot.
                regex = r"^.+@.+\\..+"
                valid = re.match(regex, email)
                if not valid:
                    return "Invalid email address"

            def open_dialog():
                assistant.add_heading("Send feedback")
                assistant.add_text_input("email", label="Email", validation=validate_email)
                result = run_dialog()
                print(result.email)



        """  # noqa: E501
        validation_function = None
        if validation:
            if isinstance(validation, str):
                validation_function = self._callbacks.robot_validation(name, validation)
            elif isinstance(validation, Callable):
                validation_function = self._callbacks.python_validation(
                    name, validation
                )
            else:
                raise ValueError("Invalid validation function.")

        if required:
            self._required_fields.add(name)

        self._client.results[name] = default

        def empty_string_to_none(e):
            if e.control.value == "":
                e.data = None

        if minimum_rows or maximum_rows:
            multiline = True
        else:
            multiline = None

        self._client.add_element(
            name=name,
            element=TextField(
                label=label,
                hint_text=placeholder,
                value=default,
                min_lines=minimum_rows,
                max_lines=maximum_rows,
                multiline=multiline,
            ),
            extra_handler=empty_string_to_none,
            validation_func=validation_function,
        )

    @keyword(tags=["input"])
    def add_password_input(
        self,
        name: str,
        label: Optional[str] = None,
        placeholder: Optional[str] = None,
    ) -> None:
        """Add a password input element

        :param name:        Name of result field
        :param label:       Label for field
        :param placeholder: Placeholder text in input field

        Adds a text field that hides the user's input. The entered
        content will be available in the ``name`` field of the result.

        For customizing the look of the input, the ``label`` text can be given
        to add a descriptive label and the ``placholder`` text can be given
        to act as an example of the input value.

        Example:

        .. code-block:: robotframework

            Add heading    Change password
            Add text input        username    label=Current username
            Add password input    password    label=New password
            ${result}=    Run dialog
            Change user password    ${result.username}  ${result.password}
        """
        self._client.add_element(
            name=name, element=TextField(label=label, value=placeholder, password=True)
        )

    @keyword(tags=["input"])
    def add_hidden_input(
        self,
        name: str,
        value: str,
    ) -> None:
        """Add a hidden input element

        :param name:  Name of result feild
        :param value: Value for input

        Adds a special hidden result field that is not visible
        to the user and always contains the given static value.

        Can be used to keep user input together with already known
        values such as user IDs, or to ensure that dialogs with differing
        elements all have the same fields in results.

        Example:

        .. code-block:: robotframework

            Add hidden input   user_id   ${USER_ID}
            Add text input     username
            ${result}=         Run dialog
            Enter user information    ${result.user_id}    ${result.username}
        """
        self._client.results[name] = value

    @keyword(tags=["input"])
    def add_file_input(
        self,
        name: str,
        label: Optional[str] = None,
        source: Optional[str] = None,
        file_type: Optional[str] = None,
        multiple: bool = False,
    ) -> None:
        """Add a file input element

        :param name:        Name of result field
        :param label:       Label for input field
        :param source:      Default source directory
        :param file_type:   Accepted file types
        :param multiple:    Allow selecting multiple files

        Adds a native file selection dialog for inputting one or more files.
        The list of selected files will be available in the ``name`` field
        of the result.

        By default opens up in the user's home directory, but it can be
        set to a custom path with the ``source`` argument.

        The argument ``file_type`` restricts the possible file extensions
        that the user can select. The format of the argument is as follows:
        ``pdf,png,svg``. For instance, an argument
        to limit options to Excel files could be: ``xls,xlsx``.

        To allow selecting more than one file, the ``multiple`` argument
        can be enabled.

        Example:

        .. code-block:: robotframework

            # This can be any one file
            Add file input    name=anything

            # This can be multiple files
            Add file input    name=multiple  multiple=True

            # This opens the select dialog to a custom folder
            Add file input    name=src       source=C:\\Temp\\Output\\

            # This restricts files to certain types
            Add file input    name=types     file_type=pdf

            # Every file input result is a list of paths
            ${result}=    Run dialog
            FOR    ${path}    IN    @{result.multiple}
                Log    Selected file: ${path}
            END
        """

        def on_pick_result(event: FilePickerResultEvent):
            if event.files:
                self._client.results[str(name)] = [f.path for f in event.files]

        file_picker = FilePicker(on_result=on_pick_result)
        self._client.add_invisible_element(file_picker)

        options = {
            "source": optional_str(source),
            "file_type": optional_str(file_type),
        }

        if not options["source"]:
            options["source"] = os.path.expanduser("~")

        if options["file_type"]:
            options["file_type"] = options["file_type"].split(",")

        self._client.add_element(
            ElevatedButton(
                label or "Choose files...",
                on_click=lambda _: file_picker.pick_files(
                    allow_multiple=bool(multiple),
                    initial_directory=options["source"],
                    allowed_extensions=options["file_type"],
                ),
            )
        )

    @keyword("Add Drop-Down", tags=["input"])
    def add_drop_down(
        self,
        name: str,
        options: Options,
        default: Optional[str] = None,
        label: Optional[str] = None,
    ) -> None:
        """Add a drop-down element

        :param name:    Name of result field
        :param options: List of drop-down options
        :param default: The default selection
        :param label:   Label for input field

        Creates a drop-down menu with the given ``options``. The selection
        the user makes will be available in the ``name`` field of the result.

        The ``default`` argument can be one of the defined options,
        and the dialog automatically selects that option for the input.

        A custom ``label`` text can also be added.

        Example:

        .. code-block:: robotframework

            Add heading     Select user type
            Add drop-down
            ...    name=user_type
            ...    options=Admin,Maintainer,Operator
            ...    default=Operator
            ...    label=User type
            ${result}=      Run dialog
            Log    User type should be: ${result.user_type}

        """
        options, default = to_options(options, default)
        options: List[Control] = list(map(Option, options))
        dropdown = Dropdown(options=options, value=default)

        self._client.results[name] = default
        self._client.add_element(Text(value=label))
        self._client.add_element(dropdown, name=str(name))

    @keyword(tags=["input"])
    def add_date_input(
        self,
        name: str,
        default: Optional[Union[date, str]] = None,
        label: Optional[str] = None,
    ) -> None:
        """Add a date input element.

        :param name:    Name of the result field
        :param default: The default set date
        :param label:   Label for the date input field

        Displays a date input widget. The selection the user makes will be available
        as a ``date`` object in the ``name`` field of the result.
        The ``default`` argument can be a pre-set date as object or string in
        "YYYY-MM-DD" format, otherwise the current date is used.

        Example:

        .. code-block:: robotframework

            Add heading       Enter your birthdate
            Add Date Input    birthdate    default=1993-04-26
            ${result} =       Run dialog
            Log To Console    User birthdate year should be: ${result.birthdate.year}
        """

        def validate(e: ControlEvent):
            date_text: str = e.data
            if not date_text:
                return None
            try:
                date.fromisoformat(date_text)
                return None
            except ValueError:
                return "Date should be in format YYYY-MM-DD"

        if default:
            if isinstance(default, str):
                try:
                    default = date.fromisoformat(default)
                except ValueError as e:
                    self.logger.error(
                        f"Default date value {default} is not in a valid ISO format."
                    )
                    raise e
            self._client.results[name] = default

        self._client.add_element(
            name=name,
            element=TextField(label=label, hint_text="YYYY-MM-DD", value=default),
            validation_func=validate,
        )

    @keyword(tags=["input"])
    def add_radio_buttons(
        self,
        name: str,
        options: Options,
        default: Optional[str] = None,
        label: Optional[str] = None,
    ) -> None:
        """Add radio button elements

        :param name:    Name of result field
        :param options: List of drop-down options
        :param default: The default selection
        :param label:   Label for input field

        Creates a set of radio buttons with the given ``options``. The selection
        the user makes will be available in the ``name`` field of the result.

        The ``default`` argument can be one of the defined options,
        and the dialog automatically selects that option for the input.

        A custom ``label`` text can also be added.

        Example:

        .. code-block:: robotframework

            Add heading     Select user type
            Add radio buttons
            ...    name=user_type
            ...    options=Admin,Maintainer,Operator
            ...    default=Operator
            ...    label=User type
            ${result}=      Run dialog
            Log    User type should be: ${result.user_type}
        """
        options, default = to_options(options, default)
        radios: List[Control] = [
            Radio(value=option, label=option) for option in options
        ]
        radio_group = RadioGroup(content=Column(radios), value=default)

        self._client.results[name] = default
        self._client.add_element(Text(value=label))
        self._client.add_element(radio_group, name=str(name))

    @keyword(tags=["input"])
    def add_checkbox(
        self,
        name: str,
        label: str,
        default: bool = False,
    ) -> None:
        """Add a checkbox element

        :param name:    Name of result field
        :param label:   Label text for checkbox
        :param default: Default checked state

        Adds a checkbox that indicates a true or false value.
        The selection will be available in the ``name`` field of the result,
        and the ``label`` text will be shown next to the checkbox.

        The boolean ``default`` value will define the initial checked
        state of the element.

        Example:

        .. code-block:: robotframework

            Add heading     Enable features
            Add checkbox    name=vault        label=Enable vault       default=True
            Add checkbox    name=triggers     label=Enable triggers    default=False
            Add checkbox    name=assistants   label=Enable assistants  default=True
            ${result}=      Run dialog
            IF    $result.vault
                Enable vault
            END
        """
        self._client.results[name] = default
        self._client.add_element(
            name=str(name), element=Checkbox(label=str(label), value=bool(default))
        )

    @keyword(tags=["input"])
    def add_submit_buttons(
        self, buttons: Options, default: Optional[str] = None
    ) -> None:
        """Add custom submit buttons

        :param buttons: Submit button options
        :param default: The primary button

        The result field will always be called ``submit`` and will contain
        the pressed button text as a value.

        If one of the custom ``options`` should be the preferred option,
        the ``default`` argument controls which one is highlighted with
        an accent color.

        Example:

        .. code-block:: robotframework

            Add icon      Warning
            Add heading   Delete user ${username}?
            Add submit buttons    buttons=No,Yes    default=Yes
            ${result}=    Run dialog
            IF   $result.submit == "Yes"
                Delete user    ${username}
            END
        """
        button_labels, default = to_options(buttons, default)

        button_elements = [
            self._create_closing_button(button) for button in button_labels
        ]
        for button in button_elements:
            self._client.add_to_disablelist(button)

        button_row = Row(button_elements, alignment=MainAxisAlignment.END)
        container = Container(button_row, alignment=alignment.bottom_right)
        self._client.add_element(container)

    @keyword(tags=["dialog"])
    def run_dialog(
        self,
        timeout: int = 180,
        title: str = "Assistant",
        height: Union[int, Literal["AUTO"]] = "AUTO",
        width: int = 480,
        on_top: bool = False,
        location: Union[WindowLocation, Tuple[int, int], None] = None,
    ) -> Result:
        """Create a dialog from all the defined elements and block
        until the user has handled it.

        :param timeout: Time to wait for dialog to complete, in seconds
        :param title:  Title of dialog
        :param height: Height of dialog (in pixels or 'AUTO')
        :param width:  Width of dialog (in pixels)
        :param on_top: Show dialog always on top of other windows
        :param location: Where to place the dialog (options are Center, TopLeft, or a
                         tuple of ints)

        If the `location` argument is `None` it will let the operating system
        place the window.

        Returns a result object with all input values.

        When the dialog closes elements are cleared.

        Example:

        .. code-block:: robotframework

            Add heading     Please enter your username
            Add text input  name=username
            ${result}=      Run dialog
            Log    The username is: ${result.username}
        """

        # height has to be either AUTO or an int value
        if not isinstance(height, int) and height != "AUTO":
            height = int(height)

        # if location is given as a string (Robot autoconversion doesn't work) parse it
        # to enum manually
        if isinstance(location, str):
            location = WindowLocation[location]

        self._client.display_flet_window(
            title, height, width, on_top, location, timeout
        )
        results = self._get_results()
        self._client.results.clear()

        return results

    def _get_results(self) -> DotDict:
        results = self._client.results
        return DotDict(**results)

    @keyword(tags=["dialog"])
    def ask_user(self, timeout: int = 180, **options: Any) -> Result:
        """Same as ``Run Dialog`` it will create a dialog from all the defined
        elements and block until the user has handled it. It will also add
        by default a submit and close buttons.

        :param timeout: Time to wait for dialog to complete, in seconds
        :param options: Options for the dialog

        Returns a result object with all input values.

        For more information about possible options for opening the dialog,
        see the documentation for the keyword ``Run Dialog``.

        Example:

        .. code-block:: robotframework

            Add heading     Please enter your username
            Add text input  name=username
            ${result}=      Ask User
            Log    The username is: ${result.username}
        """

        self.add_submit_buttons(["Submit", "Close"], "Submit")
        return self.run_dialog(**options, timeout=timeout)

    @keyword(tags=["dialog", "running"])
    def refresh_dialog(self):
        """Can be used to update UI elements when adding elements while dialog is
        running
        """
        self._client.update_elements()

    @keyword(tags=["dialog"])
    def add_button(
        self,
        label: str,
        function: Union[Callable, str],
        *args,
        location: VerticalLocation = VerticalLocation.Left,
        **kwargs,
    ) -> None:
        """Create a button and execute the `function` as a callback when pressed.

        :param label: Text for the button
        :param function: Python function or Robot Keyword name, that will get ``*args``
            and ``**kwargs`` passed into it

        Example:

        .. code-block:: robotframework

            *** Keywords ***
            First View
                Add Heading  Here is the first view of the app
                Add Button  Change View  Second View

            Second View
                Add Heading  Let's build an infinite loop
                Add Button  Change View  First View
        """

        def on_click(_: ControlEvent):
            self._callbacks.queue_fn_or_kw(function, *args, **kwargs)

        button = ElevatedButton(label, on_click=on_click)
        container = Container(alignment=location.value, content=button)
        self._client.add_element(container)
        self._client.add_to_disablelist(button)

    @keyword(tags=["dialog"])
    def add_next_ui_button(self, label: str, function: Union[Callable, str]):
        """Create a button that leads to the next UI page, calling the passed
        keyword or function, and passing current form results as first positional
        argument to it.

        :param label: Text for the button
        :param function: Python function or Robot Keyword name, that will take form
            results as its first argument

        Example:

        .. code-block:: robotframework

            *** Keywords ***
            Retrieve User Data
                # Retrieves advanced data that needs to be displayed

            Main Form
                Add Heading  Username input
                Add Text Input  name=username_1  placeholder=username
                Add Next Ui Button        Show customer details  Customer Details

            Customer Details
                [Arguments]  ${form}
                ${user_data}=  Retrieve User Data  ${form}[username_1]
                Add Heading  Retrieved Data
                Add Text  ${user_data}[phone_number]
                Add Text  ${user_data}[address]
        """

        def on_click(_: ControlEvent):
            self._callbacks.queue_fn_or_kw(function, self._get_results())

        button = ElevatedButton(label, on_click=on_click)
        self._client.add_element(button)
        self._client.add_to_disablelist(button)

    @keyword(tags=["input"])
    def add_slider(
        self,
        name: str,
        slider_min: Union[int, float] = 0,
        slider_max: Union[int, float] = 100,
        thumb_text="{value}",
        steps: Optional[int] = None,
        default: Optional[Union[int, float]] = None,
        decimals: Optional[int] = 1,
    ):
        """Add a slider input.

        :param name:        Name of result field
        :param slider_min:  Minimum value of the slider
        :param slider_max:  Maximum value of the slider
        :param thumb_label: Text to display when the slider is being slided. Use the
                            placeholder {value} for the number. (thumb text `{value%}`
                            will display values: `0%`, `100%`)
        :param steps:       Amount of steps for the slider. If None, the slider will be
                            continuous.
                            For integer output, specify a steps value where all the
                            steps will be integers, or implement rounding when
                            retrieving the result.
        :param default:     Default value for the slider. Must be between min and max.
        :param decimals:    How many decimals should the value have and show.

        .. code-block:: robotframework

            *** Keywords ***
            Create Percentage Slider
                Add Text    Percentage slider
                Add Slider  name=percentage  slider_min=0  slider_max=100
                            thumb_text={value}%  steps=100  round=1

        """
        if default:
            default = float(default)

            # Is this even necessary?
            if default.is_integer():
                default = int(default)

            if slider_min > default or slider_max < default:
                raise ValueError(f"Slider {name} had an out of bounds default value.")
            self._client.results[name] = default

        slider = Slider(
            min=slider_min,
            max=slider_max,
            divisions=steps,
            label=thumb_text,
            value=default,
            round=decimals,
        )
        self._client.add_element(name=name, element=slider)

    @keyword(tags=["dialog", "running"])
    def add_loading_spinner(
        self,
        name: str,
        width: int = 16,
        height: int = 16,
        stroke_width: int = 2,
        color: Optional[str] = None,
        tooltip: Optional[str] = None,
        value: Optional[float] = None,
    ):
        """Add a loading spinner.

        :param name:        Name of the element
        :param width:       Width of the spinner
        :param height:      Height of the spinner
        :param stroke_width: Width of the spinner's stroke
        :param color:       Color of the spinner's stroke.
                            Allowed values are colors from
                            [https://github.com/flet-dev/flet/blob/035b00104f782498d084c2fd7ee96132a542ab7f/sdk/python/packages/flet-core/src/flet_core/colors.py#L37|Flet Documentation] (in the format ``black12``, ``red500``)
                            or ARGB/RGB (#FFXXYYZZ or #XXYYZZ).XXYYZZ
        :param tooltip:     Tooltip to be displayed
                            on mouse hover.
        :param value:       Between 0.0 and 1.0 if you want to manually control it's completion.
                            If `None` it will spin endlessy.
        """  # noqa: E501
        pr = flet.ProgressRing(
            width=width,
            height=height,
            stroke_width=stroke_width,
            color=color,
            tooltip=tooltip,
            value=value,
        )
        self._client.add_element(pr, name)
        return pr

    @keyword(tags=["dialog", "running"])
    def add_loading_bar(
        self,
        name: str,
        width: int = 16,
        bar_height: int = 16,
        color: Optional[str] = None,
        tooltip: Optional[str] = None,
        value: Optional[float] = None,
    ):
        """Add a loading bar.

        :param name:        Name of the element
        :param width:       Width of the bar
        :param bar_height:  Height of the bar
        :param color:       Color of the bar's stroke.
                            Allowed values are colors from
                            [https://github.com/flet-dev/flet/blob/035b00104f782498d084c2fd7ee96132a542ab7f/sdk/python/packages/flet-core/src/flet_core/colors.py#L37|Flet Documentation] (in the format ``black12``, ``red500``)
                            or ARGB/RGB (#FFXXYYZZ or #XXYYZZ).XXYYZZ
        :param tooltip:     Tooltip to be displayed on mouse hover.
        :param value:       Between 0.0 and 1.0 if you want to manually control it's completion.
                            Use `None` for indeterminate progress indicator.
        """  # noqa: E501
        pb = flet.ProgressBar(
            width=width,
            bar_height=bar_height,
            color=color,
            tooltip=tooltip,
            value=value,
        )
        self._client.add_element(pb, name)
        return pb

    @keyword(tags=["dialog", "running"])
    def set_title(self, title: str):
        """Set dialog title when it is running."""
        self._client.set_title(title)

    def _close_layouting_element(self, layouting_element: str):
        """Check if the last opened layout element matches what is being closed,
        otherwise raise `ValueError`. If the check passes, close the layout element.
        """
        if not self._open_layouting:
            raise LayoutError(f"Cannot close {layouting_element}, no open layout")

        last_opened = self._open_layouting[-1]
        if not last_opened == layouting_element:
            raise LayoutError(
                f"Cannot close {layouting_element}, last opened layout is {last_opened}"
            )

        self._client.close_layout()
        self._open_layouting.pop()

    @keyword(tags=["layout"])
    def open_row(self):
        """Open a row layout container. Following ``Add <element>`` calls will add
        items into that row until ``Close Row`` is called.

        .. code-block:: robotframework

            *** Keywords ***
            Side By Side Elements
                Open Row
                Add Text  First item on the row
                Add Text  Second item on the row
                Close Row
        """
        self._open_layouting.append("Row")
        self._client.add_layout(Row())

    @keyword(tags=["layout"])
    def close_row(self):
        """Close previously opened row.

        Raises LayoutError if called with no Row open, or if another layout element was
        opened more recently than a row.
        """
        self._close_layouting_element("Row")

    @keyword(tags=["layout"])
    def open_container(
        self,
        margin: Optional[int] = 5,
        padding: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        background_color: Optional[str] = None,
        location: Union[Location, Tuple[int, int], None] = None,
    ):
        """Open a single element container. The following ``Add <element>`` calls adds
        an element inside the container. Can be used for styling elements.


        :param margin: How much margin to add around the container. RPA.Assistant adds
                       by default a container of margin 5 around all elements, to have
                       a smaller margin use containers with smaller margin value for
                       elements.
        :param padding: How much padding to add around the content of the container.
        :param width: Width of the container.
        :param height: Height of the container.

        :param bgcolor:   Background color for the container. Default depends on icon.
                          Allowed values are colors from
                          [https://github.com/flet-dev/flet/blob/035b00104f782498d084c2fd7ee96132a542ab7f/sdk/python/packages/flet-core/src/flet_core/colors.py#L37|Flet Documentation] (in the format ``black12``, ``red500``)
                          or ARGB/RGB (#FFXXYYZZ or #XXYYZZ).XXYYZZ
        :param location:  Where to place the container (A Location value or tuple of
                          ints). Only works inside a Stack layout element.

                          To use any Center___ or ___Center locations you must define
                          width and height to the element.


        .. code-block:: robotframework

            *** Keywords ***
            Padded Element With Background
                Open Container  padding=20  background_color=blue500
                Add Text        sample text
                Close Container


        """  # noqa: E501
        self._open_layouting.append("Container")
        if not location:
            top, left, bottom, right = None, None, None, None
        else:
            parent_height, parent_width = self._client.get_layout_dimensions()
            parsed_location = location_to_absolute(
                location, parent_width, parent_height, width, height
            )
            top = parsed_location.get("top")
            left = parsed_location.get("left")
            right = parsed_location.get("right")
            bottom = parsed_location.get("bottom")
        self._client.add_layout(
            Container(
                margin=margin,
                padding=padding,
                width=width,
                height=height,
                bgcolor=background_color,
                top=top,
                left=left,
                bottom=bottom,
                right=right,
            )
        )

    @keyword(tags=["layout"])
    def close_container(self):
        """Close previously opened container.

        Raises LayoutError if called with no Row open, or if another layout element was
        opened more recently than a row.
        """
        self._close_layouting_element("Container")

    @keyword(tags=["layout"])
    def open_navbar(self, title: Optional[str] = None):
        """Create a Navigation Bar. Following ``Add <element>`` calls will add
        items into the Navbar until ``Close Navbar`` is called.

        Navbar doesn't clear when Clear Dialog is called.

        Only one Navbar can be initialized at a time. Trying to make a second one will
        raise a LayoutError.

        .. code-block:: robotframework

            *** Keywords ***
                Go To Start Menu
                    Add Heading  Start menu
                    Add Text  Start menu content

                Assistant Navbar
                    Open Navbar  title=Assistant
                    Add Button   menu  Go To Start Menu
                    Close Navbar
        """
        self._open_layouting.append("AppBar")
        self._client.set_appbar(AppBar(title=Text(title)))

    @keyword(tags=["layout"])
    def close_navbar(self):
        """Close previously opened navbar.

        Raises LayoutError if called with no Row open, or if another layout element was
        opened more recently than a row."""
        self._close_layouting_element("AppBar")

    @keyword(tags=["layout"])
    def open_stack(self, width: Optional[int] = None, height: Optional[int] = None):
        """Create a "Stack" layout element. Stack can be used to position elements
        absolutely and to have overlapping elements in your layout. Use Container's
        `top` and `left` arguments to position the elements in a stack.

        .. code-block:: robotframework

            *** Keywords ***
                Absolutely Positioned Elements
                    # Positioning containers with relative location values requires
                    # absolute size for the Stack
                    Open Stack  height=360  width=360

                    Open Container  width=64  height=64  location=Center
                    Add Text  center
                    Close Container

                    Open Container  width=64  height=64  location=TopRight
                    Add Text  top right
                    Close Container

                    Open Container  width=64  height=64  location=BottomRight
                    Add Text  bottom right
                    Close Container

                    Close Stack

        """
        self._open_layouting.append("Stack")
        self._client.add_layout(Stack(width=width, height=height))

    @keyword(tags=["layout"])
    def close_stack(self):
        """Close previously opened Stack.

        Raises LayoutError if called with no Stack open, or if another layout element
        was opened more recently than a Stack.
        """
        self._close_layouting_element("Stack")

    @keyword(tags=["layout"])
    def open_column(self):
        """Open a Column layout container. Following ``Add <element>`` calls will add
        items into that Column until ``Close Column`` is called.

        .. code-block:: robotframework

            *** Keywords ***
            Double Column Layout
                Open Row
                Open Column
                Add Text      First item in the first column
                Add Text      Second item on the first column
                Close Column
                Open Column
                Add Text      First item on the second column
                Close Column
                Close Row
        """
        self._open_layouting.append("Column")
        self._client.add_layout(Column())

    @keyword(tags=["layout"])
    def close_column(self):
        """Closes previously opened Column.

        Raises LayoutError if called with no Column open, or if another layout element
        was opened more recently than a Column.
        """

        self._close_layouting_element("Column")
