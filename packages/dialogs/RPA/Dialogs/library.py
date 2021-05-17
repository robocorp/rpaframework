import atexit
import base64
import glob
import logging
import mimetypes
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Generator

from robot.api.deco import library, keyword  # type: ignore
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError  # type: ignore

from .dialog import Dialog, TimeoutException
from .dialog_types import Elements, Result, Options, Size, Icon
from .utils import to_options, optional_str, optional_int, int_or_auto, is_input


@library(scope="GLOBAL", doc_format="REST", auto_keywords=False)
class Dialogs:
    """The `Dialogs` library provides a way to display information to a user
    and request input while a robot is running. It allows building processes
    that require human interaction.

    Some examples of use-cases could be the following:

    - Displaying generated files after an execution is finished
    - Displaying dynamic and user-friendly error messages
    - Requesting passwords or other personal information
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
        self.elements: Elements = []
        self.dialogs: List[Dialog] = []

        try:
            # Prevent logging from keywords that return results
            keywords = [
                "Run dialog",
                "Wait dialog",
                "Wait all dialogs",
            ]
            BuiltIn().import_library(
                "RPA.core.logger.RobotLogListener", "WITH NAME", "RPA.RobotLogListener"
            )
            listener = BuiltIn().get_library_instance("RPA.RobotLogListener")
            listener.register_protected_keywords(keywords)
        except RobotNotRunningError:
            pass

    def add_element(self, element: Dict[str, Any]) -> None:
        if is_input(element):
            name = element["name"]
            names = [
                el["name"] for el in self.elements if el["type"].startswith("input-")
            ]

            if name in names:
                raise ValueError(f"Input with name '{name}' already exists")

            if name == "submit":
                raise ValueError("Input name 'submit' is not allowed")

        self.elements.append(element)

    @keyword("Clear elements")
    def clear_elements(self) -> None:
        """Remove all previously defined elements and start from a clean state

        By default this is done automatically when a dialog is created.

        Example:

        .. code-block:: robotframework

            Add heading     Please input user information
            FOR    ${user}   IN    @{users}
                Run dialog    clear=False
                Process page
            END
            Clear elements
        """
        self.elements = []

    @keyword("Add heading")
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

        element = {
            "type": "heading",
            "value": str(heading),
            "size": size.value,
        }

        self.add_element(element)

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

        element = {
            "type": "text",
            "value": str(text),
            "size": size.value,
        }

        self.add_element(element)

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
        element = {
            "type": "link",
            "value": str(url),
            "label": optional_str(label),
        }

        self.add_element(element)

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
        try:
            is_file = Path(url_or_path).is_file()
        except OSError:
            is_file = False

        if is_file:
            # Serve local files as data-uri, since the webview component
            # most likely can't serve the file directly
            mime, _ = mimetypes.guess_type(url_or_path)
            with open(url_or_path, "rb") as fd:
                data = base64.b64encode(fd.read()).decode()
                value = f"data:{mime};base64,{data}"
        else:
            # Assume image is a remote URL, which can be used as-is
            value = url_or_path

        element = {
            "type": "image",
            "value": str(value),
            "width": optional_int(width),
            "height": optional_int(height),
        }

        self.add_element(element)

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

        element = {
            "type": "file",
            "value": str(resolved),
            "label": optional_str(label),
        }

        self.add_element(element)

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

        element = {
            "type": "icon",
            "variant": variant.value,
            "size": int(size),
        }

        self.add_element(element)

    @keyword("Add text input", tags=["input"])
    def add_text_input(
        self,
        name: str,
        label: Optional[str] = None,
        placeholder: Optional[str] = None,
        rows: Optional[int] = None,
    ) -> None:
        """Add a text input element

        :param name:        Name of result field
        :param label:       Label for field
        :param placeholder: Placeholder text in input field
        :param rows:        Number of input rows

        Adds a text field that can be filled by the user. The entered
        content will be available in the ``name`` field of the result.

        For customizing the look of the input, the ``label`` text can be given
        to add a descriptive label and the ``placholder`` text can be given
        to act as an example of the input value.

        If the ``rows`` argument is given as a number, the input is converted
        into a larger text area input with the given amount of rows by default.

        Example:

        .. code-block:: robotframework

            Add heading    Send feedback
            Add text input    email    label=E-mail address
            Add text input    message
            ...    label=Feedback
            ...    placeholder=Enter feedback here
            ...    rows=5
            ${result}=    Run dialog
            Send feedback message    ${result.email}  ${result.message}
        """
        element = {
            "type": "input-text",
            "name": str(name),
            "label": optional_str(label),
            "placeholder": optional_str(placeholder),
            "rows": optional_int(rows),
        }

        self.add_element(element)

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
        element = {
            "type": "input-password",
            "name": str(name),
            "label": optional_str(label),
            "placeholder": optional_str(placeholder),
        }

        self.add_element(element)

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
        element = {
            "type": "input-hidden",
            "name": str(name),
            "value": str(value),
        }

        self.add_element(element)

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
        ``Description text (*.ext1;*.ext2;...)``. For instance, an argument
        to limit options to Excel files could be: ``Excel files (*.xls;*.xlsx)``.

        To allow selecting more than one file, the ``multiple`` argument
        can be enabled.

        Example:

        .. code-block:: robotframework

            # This can be any one file
            Add file input    name=anyting

            # This can be multiple files
            Add file input    name=multiple  multiple=True

            # This opens the select dialog to a custom folder
            Add file input    name=src       source=C:\\Temp\\Output\\

            # This copies selected files to a custom folder
            Add file input    name=dest      destination=%{ROBOT_ROOT}

            # This restricts files to certain types
            Add file input    name=types     file_type=PDF files (*.pdf)

            # Every file input result is a list of paths
            ${result}=    Run dialog
            FOR    ${path}    IN    @{result.multiple}
                Log    Selected file: ${path}
            END
        """
        element = {
            "type": "input-file",
            "name": str(name),
            "label": optional_str(label),
            "source": optional_str(source),
            "destination": optional_str(destination),
            "file_type": optional_str(file_type),
            "multiple": bool(multiple),
        }

        self.add_element(element)

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

        element = {
            "type": "input-dropdown",
            "name": str(name),
            "options": options,
            "default": default,
            "label": optional_str(label),
        }

        self.add_element(element)

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

        element = {
            "type": "input-radio",
            "name": str(name),
            "options": options,
            "default": default,
            "label": optional_str(label),
        }

        self.add_element(element)

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
        element = {
            "type": "input-checkbox",
            "name": str(name),
            "label": str(label),
            "default": bool(default),
        }

        self.add_element(element)

    @keyword("Add submit buttons", tags=["input"])
    def add_submit_buttons(
        self,
        buttons: Options,
        default: Optional[str] = None,
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
        buttons, _ = to_options(buttons, default)

        element = {
            "type": "submit",
            "buttons": buttons,
            "default": default,
        }

        self.add_element(element)

    @keyword("Run dialog", tags=["dialog"])
    def run_dialog(self, timeout: int = 180, **options: Any) -> Result:
        """Create a dialog from all the defined elements and block
        until the user has handled it.

        :param timeout: Time to wait for dialog to complete, in seconds
        :param options: Options for the dialog

        Returns a result object with all input values.
        This keyword is a shorthand for the following expression:

        .. code-block:: robotframework

            Run dialog
                [Arguments]  ${timeout}=180  &{options}
                ${dialog}=   Show dialog     &{options}
                ${result}=   Wait dialog     ${dialog}  timeout=${timeout}
                [Return]     ${result}

        For more information about possible options for opening the dialog,
        see the documentation for the keyword ``Show dialog``.

        Example:

        .. code-block:: robotframework

            Add heading     Please enter your username
            Add text input  name=username
            ${result}=      Run dialog
            Log    The username is: ${result.username}
        """
        dialog = self.show_dialog(**options)
        return self.wait_dialog(dialog, timeout)

    @keyword("Show dialog", tags=["dialog"])
    def show_dialog(
        self,
        title: str = "Dialog",
        height: Union[int, str] = "AUTO",
        width: int = 480,
        on_top: bool = False,
        clear: bool = True,
        debug: bool = False,
    ) -> Dialog:
        """Create a new dialog with all the defined elements, and show
        it to the user. Does not block, but instead immediately returns
        a new ``Dialog`` instance.

        The return value can later be used to wait for
        the user to close the dialog and inspect the results.

        :param title:  Title of dialog
        :param height: Height of dialog (in pixels or 'AUTO')
        :param width:  Width of dialog (in pixels)
        :param on_top: Show dialog always on top of other windows
        :param clear:  Remove all defined elements
        :param debug:  Allow opening developer tools in Dialog window

        By default the window has the title ``Dialog``, but it can be changed
        with the argument ``title`` to any string.

        The ``height`` argument accepts a static number in pixels, but
        defaults to the string value ``AUTO``. In this mode the Dialog window
        tries to automatically resize itself to fit the defined content.

        In comparison, the ``width`` argument only accepts pixel values, as all
        element types by default resize to fit the given window width.

        With the ``clear`` argument it's possible to control if defined elements
        should be cleared after the dialog has been created. It can be set
        to ``False`` if the same content should be shown multiple times.

        In certain applications it's useful to have the dialog always be
        on top of already opened applications. This can be set with the
        argument ``on_top``, which is disabled by default.

        For development purposes the ``debug`` agument can be enabled to
        allow opening browser developer tools.

        If the dialog is still open when the execution ends, it's closed
        automatically.

        Example:

        .. code-block:: robotframework

            Add text input    name=username    label=Username
            Add text input    name=address     label=Address
            ${dialog}=    Show dialog    title=Input form
            Open browser to form page
            ${result}=    Wait dialog    ${dialog}
            Insert user information      ${result.username}  ${result.address}
        """
        height = int_or_auto(height)
        dialog = Dialog(
            self.elements,
            title=title,
            height=height,
            width=width,
            on_top=on_top,
            debug=debug,
        )

        if clear:
            self.clear_elements()

        dialog.start()
        self.dialogs.append(dialog)
        atexit.register(dialog.stop)

        return dialog

    @keyword("Wait dialog", tags=["dialog"])
    def wait_dialog(self, dialog: Dialog, timeout: int = 300) -> Result:
        """Wait for a dialog to complete that has been created with the
        keyword ``Show dialog``.

        :param dialog:  An instance of a Dialog
        :param timeout: Time to wait for dialog to complete, in seconds

        Blocks until a user has closed the dialog or until ``timeout``
        amount of seconds has been reached.

        If the user submitted the dialog, returns a result object.
        If the user closed the dialog window or ``timeout`` was reached,
        raises an exception.

        Example:

        .. code-block:: robotframework

            Add text input    name=username    label=Username
            Add text input    name=address     label=Address
            ${dialog}=    Show dialog    title=Input form
            Open browser to form page
            ${result}=    Wait dialog    ${dialog}
            Insert user information      ${result.username}  ${result.address}
        """
        dialog.wait(timeout)
        return dialog.result()

    @keyword("Wait all dialogs", tags=["dialog"])
    def wait_all_dialogs(self, timeout: int = 300) -> List[Result]:
        """Wait for all opened dialogs to be handled by the user.

        :param timeout: Time to wait for dialogs to complete, in seconds

        Returns a list of results from all dialogs that have not been handled
        before calling this keyword, in the order the dialogs
        were originally created.

        If any dialog fails, this keyword throws the corresponding exception
        immediately and doesn't keep waiting for further results.

        Example:

        .. code-block:: robotframework

            # Create multiple dialogs
            Show dialog    title=One
            Show dialog    title=Two
            Show dialog    title=Three

            # Wait for all of them to complete
            @{results}=    Wait all dialogs

            # Loop through results
            FOR    ${result}    IN    @{results}
                Log many    &{result}
            END
        """
        # Filter dialogs that have been handled already
        pending = [dialog for dialog in self.dialogs if dialog.is_pending]

        results = []
        for dialog in self.wait_dialogs_as_completed(*pending, timeout=timeout):
            results.append((dialog, dialog.result()))

        # Sort by dialog creation timestamp
        results.sort(key=lambda t: t[0].timestamp)

        return [result for _, result in results]

    @keyword("Close dialog", tags=["dialog"])
    def close_dialog(self, dialog: Dialog) -> None:
        """Close a dialog that has been created with the keyword
        ``Show dialog``.

        :param dialog: An instance of a Dialog

        Calling this keyword is not required if the user correctly
        submits a dialog or closes it manually. However, it can be used
        to forcefully hide a dialog if the result is no longer relevant.

        If a forcefully closed dialog is waited, it will throw
        an exception to indicate that it was closed before receiving
        a valid result.

        Example:

        .. code-block:: robotframework

            # Display notification dialog while operation runs
            ${dialog}=    Show dialog    title=Please wait
            Run process that takes a while
            Close dialog    ${dialog}
        """
        dialog.stop()

    @keyword("Close all dialogs", tags=["dialog"])
    def close_all_dialogs(self) -> None:
        """Close all dialogs opened by this library.

        See the keyword ``Close dialog`` for further information
        about usage and implications.

        Example:

        .. code-block:: robotframework

            ${dialog1}=    Show dialog
            A keyword which runs during the dialog

            ${dialog2}=    Show dialog
            A keyword that fails during the dialog

            # Close all dialogs without knowing which have been created
            [Teardown]    Close all dialogs
        """
        for dialog in self.dialogs:
            dialog.stop()

    def wait_dialogs_as_completed(
        self, *dialogs: Dialog, timeout: int = 300
    ) -> Generator[Dialog, None, None]:
        """Create a generator that yields dialogs as they complete.

        :param dialogs: Dialogs to wait
        :param timeout: Time in seconds to wait for all dialogs
        """
        if not dialogs:
            return

        index = list(range(len(dialogs)))

        end = time.time() + timeout
        while time.time() <= end:
            if not index:
                return

            for idx in list(index):
                dialog = dialogs[idx]
                if dialog.poll():
                    self.logger.info(
                        "Dialog completed (%s/%s)",
                        len(dialogs) - len(index) + 1,
                        len(dialogs),
                    )
                    yield dialog
                    index.remove(idx)

            time.sleep(0.1)

        raise TimeoutException("Reached timeout while waiting for dialogs")
