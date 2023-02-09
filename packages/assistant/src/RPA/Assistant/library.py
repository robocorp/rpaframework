import glob
import logging
import os
import platform
import subprocess
from datetime import date
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, Literal

import flet
from flet import (
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
    Text,
    TextField,
    alignment,
    colors,
    icons,
)
from flet.control_event import ControlEvent
from flet.dropdown import Option
from robot.api.deco import keyword, library
from robot.errors import RobotError
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError

from RPA.Assistant.flet_client import FletClient
from RPA.Assistant.types import Icon, Options, Result, Size, Location
from RPA.Assistant.utils import (
    optional_str,
    to_options,
)


@library(scope="GLOBAL", doc_format="REST", auto_keywords=False)
class Assistant:
    """The `Assistant` library provides a way to display information to a user
    and request input while a robot is running. It allows building processes
    that require human interaction. Also it offers capabilities of running
    other robots inside the current one and determine what to display to the
    user based on his previous responses.

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
    error, the library will raise an exception and the result values will
    not be available.

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
            ...    rows=5
            ${result}=    Run dialog
            Send feedback message    ${result.email}  ${result.message}

        Dialog as progress indicator
            Add heading    Please wait while I open a browser
            ${dialog}=     Show dialog    title=Please wait    on_top=${TRUE}
            Open available browser    https://robocorp.com
            Close dialog   ${dialog}
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self._client = FletClient()
        self._validations: Dict[str, Callable] = {}
        # Disable fletd debug logging
        os.environ["GIN_MODE"] = "release"

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
            should_close = True
            if not self._validations:
                self._client.page.window_destroy()
            for field_name, validation in self._validations.items():
                if not validation or field_name not in self._client.results:
                    continue
                error_message = validation(self._client.results[field_name])
                if error_message:
                    should_close = False
                    self._client.page.add(
                        Text(
                            f"Error on field named '{field_name}: {error_message}",
                            color=flet.colors.RED,
                        )
                    )
                    self._client.page.update()
            if should_close:
                self._client.results["submit"] = label
                self._client.page.window_destroy()

        return ElevatedButton(label, on_click=validate_and_close)

    @keyword("Clear dialog")
    def clear_dialog(self) -> None:
        """Remove all previously defined elements and start from a clean state.
        By default this is done automatically when a dialog is created.
        It will also clear all the results.

        Example:

        .. code-block:: robotframework

            Add heading     Please input user information
            FOR    ${user}   IN    @{users}
                Run dialog    clear=False
                Process page
            END
            Clear dialog
        """
        self._client.results = {}
        self._client.clear_elements()

    @keyword("Add Heading")
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

    @keyword("Add text")
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

    @keyword("Add link")
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

    @keyword("Add image")
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

    @keyword("Add file")
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

    @keyword("Add files")
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

    @keyword("Add icon")
    def add_icon(self, variant: Icon, size: int = 48) -> None:
        """Add an icon element

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

    @keyword("Add text input", tags=["input"])
    def add_text_input(
        self,
        name: str,
        label: Optional[str] = None,
        placeholder: Optional[str] = None,
        validation: Union[Callable, None] = None,
    ) -> None:
        """Add a text input element

        :param name:        Name of result field
        :param label:       Label for field
        :param placeholder: Placeholder text in input field
        :param validation:   Validation function for the input field

        Adds a text field that can be filled by the user. The entered
        content will be available in the ``name`` field of the result.

        For customizing the look of the input, the ``label`` text can be given
        to add a descriptive label and the ``placholder`` text can be given
        to act as an example of the input value.

        Example:

        .. code-block:: robotframework

            Add heading    Send feedback
            Add text input    email    label=E-mail address
            Add text input    message
            ...    label=Feedback
            ...    placeholder=Enter feedback here
            ${result}=    Run dialog
            Send feedback message    ${result.email}  ${result.message}
        """
        # TODO: Implement the rows support
        if validation:
            self._validations[name] = validation

        self._client.add_element(
            name=name, element=TextField(label=label, hint_text=placeholder)
        )

    @keyword("Add password input", tags=["input"])
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

    @keyword("Add hidden input", tags=["input"])
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

    @keyword("Add file input", tags=["input"])
    def add_file_input(
        self,
        name: str,
        label: Optional[str] = None,
        source: Optional[str] = None,
        destination: Optional[str] = None,
        file_type: Optional[str] = None,
        multiple: bool = False,
    ) -> None:
        """Add a file input element

        :param name:        Name of result field
        :param label:       Label for input field
        :param source:      Default source directory
        :param destination: Target directory for selected files
        :param file_type:   Accepted file types
        :param multiple:    Allow selecting multiple files

        Adds a native file selection dialog for inputting one or more files.
        The list of selected files will be available in the ``name`` field
        of the result.

        By default opens up in the user's home directory, but it can be
        set to a custom path with the ``source`` argument.

        If the ``destination`` argument is not set, it returns the original
        paths to the selected files. If the ``destination`` directory
        is set, the files are copied there first and the new paths are
        returned.

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

            # This copies selected files to a custom folder
            Add file input    name=dest      destination=%{ROBOT_ROOT}

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
            "destination": optional_str(destination),
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
                    initial_directory=options["destination"],
                    allowed_extensions=options["file_type"],
                ),
            )
        )

    @keyword("Add drop-down", tags=["input"])
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

        self._client.add_element(Text(value=label))
        self._client.add_element(dropdown, name=str(name))

    @keyword("Add Date Input", tags=["input"])
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

        def validate(date_text):
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

        self._validations[name] = validate
        self._client.add_element(
            name=name,
            element=TextField(label=label, hint_text="YYYY-MM-DD", value=default),
        )

    @keyword("Add radio buttons", tags=["input"])
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

        self._client.add_element(Text(value=label))
        self._client.add_element(radio_group, name=str(name))

    @keyword("Add checkbox", tags=["input"])
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
        self._client.add_element(
            name=str(name), element=Checkbox(label=str(label), value=bool(default))
        )

    @keyword("Add submit buttons", tags=["input"])
    def add_submit_buttons(
        self, buttons: Options, default: Optional[str] = None
    ) -> None:
        """Add custom submit buttons

        :param buttons: Submit button options
        :param default: The primary button

        The dialog automatically creates a button for closing itself.
        If there are no input fields, the button will say "Close".
        If there are one or more input fields, the button will say "Submit".

        If the submit button should have a custom label or there should be
        multiple options to choose from  when submitting, this keyword can
        be used to replace the automatically generated ones.

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

    @keyword("Run dialog", tags=["dialog"])
    def run_dialog(
        self,
        timeout: int = 180,
        title: str = "Dialog",
        height: Union[int, Literal["AUTO"]] = "AUTO",
        width: int = 480,
        on_top: bool = False,
        location: Union[Location, Tuple[int, int], None] = None,
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

        None will let the operating system place the window.


        Returns a result object with all input values.

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
            location = Location[location]

        self._client.display_flet_window(
            title, height, width, on_top, location, timeout
        )
        return self._client.results

    @keyword("Ask User", tags=["dialog"])
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

    @keyword("Refresh Dialog", tags=["dialog"])
    def refresh_dialog(self):
        """Can be used to update UI elements when adding elements while dialog is
        running
        """
        if self._client.page:
            self._client.update_elements(self._client.page)
        else:
            raise RuntimeError("No dialog open")

    def _create_python_function_wrapper(self, function, *args, **kwargs):
        """wrapper code that is used to add wrapping for user functions when binding
        them to be run by buttons
        """

        def func_wrapper():
            try:
                function(*args, **kwargs)

            # This can be anything since it comes from the user function, we don't
            # want to let the user function crash the UI
            except Exception as err:  # pylint: disable=broad-except
                self.logger.error(f"Error calling Python function {function}")
                self.logger.error(err)
            finally:
                self._client.unlock_elements()
                self._client.flet_update()

        return func_wrapper

    def _create_robot_function_wrapper(self, function, *args, **kwargs):
        """wrapper code that is used to add wrapping for user functions when binding
        them to be run by buttons
        """

        def func_wrapper():
            try:
                BuiltIn().run_keyword(function, *args, **kwargs)
            except RobotNotRunningError:
                self.logger.error(
                    f"Robot Framework not running so cannot call keyword {function}"
                )
            except RobotError as e:
                self.logger.error(f"Error calling robot keyword {function}")
                self.logger.error(e)
            # This can be anything since it comes from the user function, we don't
            # want to let the user function crash the UI
            except Exception as err:  # pylint: disable=broad-except
                self.logger.error(f"Unexpected error running robot keyword {function}")
                self.logger.error(err)
            finally:
                self._client.unlock_elements()
                self._client.flet_update()

        return func_wrapper

    def _queue_function_or_robot_keyword(
        self, function: Union[Callable, str], *args, **kwargs
    ):
        """Check if function is a Python function or a Robot Keyword, and call it
        or run it with Robot's run_keyword.
        """
        if self._client.pending_operation:
            self.logger.error("Can't have more than one pending operation.")
            return
        self._client.lock_elements()
        self._client.flet_update()

        if isinstance(function, Callable):
            self._client.pending_operation = self._create_python_function_wrapper(
                function, *args, **kwargs
            )
        else:
            self._client.pending_operation = self._create_robot_function_wrapper(
                function, *args, **kwargs
            )

    @keyword("Add Button", tags=["dialog"])
    def add_button(
        self, label: str, function: Union[Callable, str], *args, **kwargs
    ) -> None:
        """
        :param label: Text for the button
        :param function: Python function or Robot Keyword name, that will get ``*args``
        and ``**kwargs`` passed into it
        """

        def on_click(_: ControlEvent):
            self._queue_function_or_robot_keyword(function, *args, **kwargs)

        button = ElevatedButton(label, on_click=on_click)
        self._client.add_element(button)
        self._client.add_to_disablelist(button)

    @keyword("Add Next Ui Button", tags=["dialog"])
    def add_next_ui_button(self, label: str, function: Union[Callable, str]):
        """Create a button that leads to the next UI page, calling the passed
        keyword or function, and passing current form results as first positional
        argument to it.

        :param label: Text for the button
        :param function: Python function or Robot Keyword name, that will take form
        results as it's first argument

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
            self._queue_function_or_robot_keyword(function, self._client.results)

        button = ElevatedButton(label, on_click=on_click)
        self._client.add_element(button)
        self._client.add_to_disablelist(button)
