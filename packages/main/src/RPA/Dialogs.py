import cgi
import json
import logging
import os
import threading
import time
from collections import OrderedDict
from datetime import datetime
from http.server import (  # pylint: disable=no-name-in-module
    BaseHTTPRequestHandler,
    HTTPServer,
)
from itertools import count
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import unquote_plus

import requests
from RPA.Browser.Selenium import Selenium

try:
    from importlib import import_module
    import importlib.resources as pkg_resources
except ImportError:
    # Try backported to PY<37 `importlib_resources`.
    import importlib_resources as pkg_resources


class Handler(BaseHTTPRequestHandler):
    """Server request handler class"""

    # pylint: disable=unused-argument, signature-differs
    def log_message(self, *args, **kwargs):
        return

    # pylint: disable=unused-argument, signature-differs
    def log_request(self, *args, **kwargs):
        pass

    def _set_response(self, response_code=200, headertype="json"):
        self.send_response(response_code)
        if headertype == "json":
            self.send_header("Content-type", "application/json")
        else:
            self.send_header("Content-type", "text/html")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def import_styles(self):
        inline_styles = "<head><style>"
        stylesheet_filepath = Path(self.server.stylepath)
        with open(stylesheet_filepath, "r") as styles:
            inline_styles += styles.read()
        inline_styles += "</style></head>"
        return inline_styles

    def get_radiobutton(self, item):
        formhtml = ""
        if "label" in item:
            formhtml += f"<p>{item['label']}</p>"
        for option in item["options"]:
            checkedvalue = ""
            if "default" in item and item["default"] == option:
                checkedvalue = " checked"
            formhtml += f"""<input type=\"radio\" id=\"{option}\" name=\"{item['id']}\"
                            value="{option}"{checkedvalue}>
                            <label for=\"{option}\">{option}</label><br>"""
        return formhtml

    def get_checkbox(self, item):
        formhtml = ""
        if "label" in item:
            formhtml += f"<p>{item['label']}</p>"
        idx = 1
        for option in item["options"]:
            checkedvalue = ""
            if "default" in item and item["default"] == option:
                checkedvalue = " checked"
            formhtml += f"""<input type=\"checkbox\" id=\"{item['id']}{idx}\"
                            name=\"{item['id']}{idx}\" value="{option}" {checkedvalue}>
                            <label for=\"{item['id']}{idx}\">{option}</label><br>"""
            idx += 1
        return formhtml

    def get_dropdown(self, item):
        formhtml = (
            f"<label for=\"{item['id']}\">{item['label']}</label><br>"
            f"<select name=\"{item['id']}\" name=\"{item['id']}\"><br>"
        )
        for option in item["options"]:
            selected = ""
            if "default" in item and item["default"] == option:
                selected = " selected"
            formhtml += f'<option name="{option}"{selected}>{option}</option>'
        formhtml += "</select><br>"
        return formhtml

    def get_submit(self, item):
        formhtml = ""
        for button in item["buttons"]:
            formhtml += f"""<input type=\"submit\" name=\"{item['name']}\"
                        value=\"{button}\">"""
        return formhtml + "<br>"

    def get_textarea(self, item):
        defaulttext = item["default"] if "default" in item else ""
        return f"""<textarea name=\"{item['name']}\" rows=\"{item['rows']}\"
                    cols=\"{item['cols']}\">{defaulttext}</textarea><br>"""

    def get_textinput(self, item):
        value = item["value"] if "value" in item else ""
        return (
            f"<label for=\"{item['name']}\">{item['label']}</label><br>"
            f"<input type=\"text\" name=\"{item['name']}\" value=\"{value}\"><br>"
        )

    def get_hiddeninput(self, item):
        return (
            f"<input type=\"hidden\" name=\"{item['name']}\""
            f"value=\"{item['value']}\"><br>"
        )

    def get_fileinput(self, item):
        accept_filetypes = (
            f"accept=\"{item['filetypes']}\"" if "filetypes" in item.keys() else ""
        )
        formhtml = (
            f"<label for=\"{item['name']}\">{item['label']}</label><br>"
            f"<input type=\"file\" id=\"{item['id']}\" "
            f"name=\"{item['name']}\" {accept_filetypes} multiple><br>"
        )
        if "target_directory" in item.keys():
            formhtml += (
                f"<input type='hidden' name='target_directory'"
                f" value=\"{item['target_directory']}\">"
            )
        return formhtml

    def get_title(self, item):
        return f"<h3>{item['value']}</h3>"

    def get_text(self, item):
        return f"<p>{item['value']}</p>"

    def create_form(self, message):
        has_submit = False
        formhtml = "<head>"
        formhtml += self.import_styles()
        formhtml += "</head>"
        formhtml += '<form action="formresponsehandling" method="post"'
        formhtml += ' enctype="multipart/form-data">'
        for item in message["form"]:
            dom_func = getattr(self, f"get_{item['type']}", "")
            formhtml += dom_func(item)
            if item["type"] == "submit":
                has_submit = True
        if not has_submit:
            formhtml += "<input type='submit' value='Submit'>"
        formhtml += "</form></body>"

        self.server.formhtml = formhtml.encode("utf-8")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_POST(self):
        if "formspec" in self.path:
            # read the message and convert it into a python dictionary
            length = int(self.headers.get("content-length"))
            message = json.loads(self.rfile.read(length), object_pairs_hook=OrderedDict)
            self.server.formresponse = None
            self.create_form(message)
            self._set_response()
        elif "formresponsehandling" in self.path:
            length = int(self.headers.get("Content-length", 0))
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": self.headers["Content-Type"],
                },
            )
            files = []
            target_directory = os.getenv("ROBOT_ROOT", str(Path.cwd()))

            response = {}
            for field in form.list or ():
                if field.filename:
                    files.append(field)
                elif field.name == "target_directory":
                    target_directory = Path(field.value).resolve()
                else:
                    response[str(field.name)] = unquote_plus(str(field.value))

            for f in files:
                field_name = str(f.name)
                os.makedirs(target_directory, exist_ok=True)
                filepath = str(target_directory / Path(f.filename))
                with open(filepath, "wb") as fw:
                    fw.write(f.file.read())
                if field_name in response.keys():
                    response[field_name].append(filepath)
                else:
                    response[field_name] = [filepath]

            self.server.formresponse = response
            self._set_response()
        else:
            self._set_response(404)

    def do_GET(self):
        if self.path.endswith("favicon.ico"):
            return

        if self.path.endswith("requestresponse"):
            if self.server.formresponse is not None:
                self._set_response(200, "json")
                self.wfile.write(json.dumps(self.server.formresponse).encode("utf-8"))
                self.server.formresponse = None
            else:
                self._set_response(304, "json")
        elif self.path == "/":
            if self.server.formhtml:
                self._set_response(200, "html")
                self.wfile.write(self.server.formhtml)
            else:
                self._set_response(404, "html")
        elif self.path.endswith(".html"):
            self._set_response(200, "html")
            if self.path == "/":
                filename = "./index.html"
            else:
                filename = "./" + self.path
            with open(filename, "rb") as fh:
                html = fh.read()
                self.wfile.write(html)
        else:
            self._set_response(404, "html")


class Dialogs:
    """The `Dialogs` library provides a way to ask for user input during executions
    through HTML forms. Form elements can be built with library keywords or they can
    be defined in a static JSON file.

    **How the library works**

    The main keyword of the library is ``Request Response`` which works as follows:

    1. It starts an HTTP server in the background
    2. The HTML form is generated either according to a JSON file or the
       keywords called during the task
    3. It opens a browser and shows the created form (The browser is opened with
       the ``Open Available Browser`` keyword from the ``RPA.Browser.Selenium`` library)
    4. Once the form is filled and submitted by the user, the server will process
       the response and extract the field values, which in turn are returned by the keyword
    5. In the end, the browser is closed and the HTTP server is stopped

    ``Request Response`` can be invoked in two ways:

    1. Without any parameters. This means that form shown is the one created
       by other library keywords. If no form elements have been added with
       keywords then the form will contain just one submit button. Form building
       must be started with the keyword ``Create Form``.
    2. Giving a path to a JSON file (using the parameter **formspec**) which
       specifies the elements that form should include.

    The keyword has optional parameters to specify form window **width** and **height**.
    The default size is 600px wide and 1000px high.

    **Setting library arguments**

    Library has arguments ``server_port`` and ``stylesheet``. The ``server_port`` argument
    takes integer value, which defines port where HTTP server will be run. By default port is 8105.
    The ``stylesheet`` can be used to point CSS file, which will be used to modify style of form,
    which is shown to the user. Defaults to built-in Robocorp stylesheet.

    **Supported element types**

    As a bare minimum, the form is displayed with a submit button when the
    ``Request Response`` keyword is called.

    The supported input elements and their corresponding HTML tags are:

    - form (``<form>``)
    - title (``<h3>``)
    - text (``<p>``)
    - radiobutton  (``<input type='radio'>``)
    - checkbox (``<input type='checkbox'>``)
    - dropdown (``<select>``)
    - textarea (``<textarea>``)
    - textinput (``<input type='text'>``)
    - fileinput (``<input type='file'>``)
    - hiddeninput (``<input type='hidden'>``)
    - submit (``<input type='submit'>``)

    **About file types**

    The ``Add File Input`` keyword has parameter ``filetypes``. Parameter sets filter
    for file types that can be uploaded via element. Parameter can be set to ``filetypes=${EMPTY}``
    to accept all files. Multiple types are separated with comma ``filetypes=image/jpeg,image/png``.

    Some common filetypes:

    - image/* (all image types)
    - audio/* (all audio types)
    - video/* (all video types)
    - application/pdf (PDFs)
    - application/vnd.ms-excel (.xls, .xlsx)

    The list of all possible `MIME-types <http://www.iana.org/assignments/media-types/media-types.xhtml>`_.

    **Examples**

    **Robot Framework**

    Examples of creating forms through keywords and a JSON file:

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Dialogs

        *** Keywords ***
        Ask Question From User By Form Built With Keywords
            Create Form     questions
            Add Text Input  label=What is your name?  name=username
            &{response}=    Request Response
            Log             Username is "${response}[username]"

        Ask Question From User By Form Specified With JSON
            &{response}=    Request Response  /path/to/myform.json
            Log             Username is "${response}[username]"

    **Python**

    The library can also be used inside Python:

    .. code-block:: python

        from RPA.Dialogs import Dialogs

        def ask_question_from_user(question, attribute):
            d = Dialogs()
            d.create_form('questions')
            d.add_text_input(label=question, name=attribute)
            response = request_response()
            return response

        response = ask_question_from_user('What is your name ?', 'username')
        print(f"Username is '{response['username']}'")
    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self, server_port: int = 8105, stylesheet: str = None):
        """The dialogs library can be initialized to a custom
        port and with a custom stylesheet for dialogs.

        :param server_port: HTTP server port, defaults to 8105
        :param stylesheet: defaults to built-in Robocorp stylesheet
        """
        self.logger = logging.getLogger(__name__)
        self.server_port = int(server_port)
        self.server_address = f"http://localhost:{self.server_port}"
        self.server = None
        self.thread = None

        self.custom_form = None
        self.stylesheet = stylesheet

        if self.stylesheet is None:
            includes = import_module("RPA.includes")
            with pkg_resources.path(includes, "dialog_styles.css") as path:
                self.stylesheet = path

    def _start_server_thread(self):
        """Start a server which will server form html and
        handles form post.
        """
        # Already running
        if self.thread and self.thread.is_alive():
            return

        # Previous server thread has died
        if self.thread and not self.thread.is_alive():
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=10)

        self.thread = threading.Thread(name="form_server", target=self._run_server)
        self.thread.daemon = True
        self.thread.start()

    def _run_server(self):
        self.logger.info("Starting server at port %d", self.server_port)

        self.server = HTTPServer(("", self.server_port), Handler)
        self.server.allow_reuse_address = True
        self.server.stylepath = self.stylesheet
        self.server.formresponse = None
        self.server.formhtml = None

        self.server.serve_forever()

    def create_form(self, title: str = None) -> None:
        """Create new form

        :param title: form title, defaults to None

        Example:

        .. code-block:: robotframework

            Create Form     # form title will be "Requesting response"
            Create Form     title=User Confirmation Form

        """
        self.custom_form = OrderedDict()
        self.custom_form["form"] = list()
        if title:
            self.add_title(title)
        self.add_hidden_input(
            name="dialogs_form_creation_date",
            value=datetime.now(),
        )

    def add_title(self, title: str) -> None:
        """Add h3 element into form

        :param title: text for the element

        Example:

        .. code-block:: robotframework

            Create Form     # default form title will be "Requesting response"
            Add Title       User Confirmation Form

        """
        element = {"type": "title", "value": title}
        self.custom_form["form"].append(element)

    def add_text_input(self, label: str, name: str, value: str = None) -> None:
        """Add text input element

        :param label: input element label
        :param name: input element name attribute
        :param value: input element value attribute

        Example:

        .. code-block:: robotframework

            Create Form
            Add Text Input   what is your firstname ?  fname   value=Mika

        """
        element = {"type": "textinput", "label": label, "name": name, "value": value}
        self.custom_form["form"].append(element)

    def add_hidden_input(self, name: str, value: str) -> None:
        """Add hidden input element

        :param name: input element name attribute
        :param value: input element value attribute

        Example:

        .. code-block:: robotframework

            Create Form
            ${uuid}   Evaluate  str(uuid.uuid4())
            Add Hidden Input    form-id   ${uuid}

        """
        element = {
            "type": "hiddeninput",
            "name": name,
            "value": str(value),
        }
        self.custom_form["form"].append(element)

    def add_file_input(
        self,
        label: str,
        element_id: str,
        name: str,
        filetypes: str,
        target_directory: str = None,
    ) -> None:
        """Add text input element

        :param label: input element label
        :param element_id: hidden element id attribute
        :param name: input element name attribute
        :param filetypes: accepted filetypes for the file upload
        :param target_directory: where to save uploaded files to

        Read more of the filetypes in the library documentation.

        Example:

        .. code-block:: robotframework

            Create Form
            Add File Input  label=Attachment
            ...             element_id=attachment
            ...             name=attachment
            ...             filetypes=${EMPTY}         # Accept all files
            ...             target_directory=${CURDIR}${/}output

            Add File Input  label=Contract
            ...             element_id=contract
            ...             name=contract
            ...             filetypes=application/pdf  # Accept only PDFs
            ...             target_directory=${CURDIR}${/}output

        """
        element = {
            "type": "fileinput",
            "label": label,
            "name": name,
            "id": element_id,
            "filetypes": filetypes,
        }
        if target_directory:
            element["target_directory"] = target_directory
        self.custom_form["form"].append(element)

    def add_dropdown(
        self, label: str, element_id: str, options: Any, default: str = None
    ) -> None:
        """Add dropdown element

        :param label: dropdown element label
        :param element_id: dropdown element id attribute
        :param options: values for the dropdown
        :param default: dropdown selected value, defaults to None

        Example:

        .. code-block:: robotframework

            Create Form
            Add Dropdown  label=Select task type
            ...           element_id=tasktype
            ...           options=buy,sell,rent
            ...           default=buy

        """
        if not isinstance(options, list):
            options = options.split(",")
        element = {
            "type": "dropdown",
            "label": label,
            "id": element_id,
            "options": options,
        }
        if default:
            element["default"] = default
        self.custom_form["form"].append(element)

    def add_submit(self, name: str, buttons: str) -> None:
        """Add submit element

        :param name: element name attribute
        :param buttons: list of buttons

        Example:

        .. code-block:: robotframework

            Create Form
            Add Submit    name=direction-to-go  buttons=left,right

        """
        if not isinstance(buttons, list):
            buttons = buttons.split(",")
        element = {"type": "submit", "name": name, "buttons": buttons}
        self.custom_form["form"].append(element)

    def add_radio_buttons(
        self, element_id: str, options: str, default: str = None
    ) -> None:
        """Add radio button element

        :param element_id: radio button element identifier
        :param options: values for the radio button
        :param default: radio button selected value, defaults to None

        Example:

        .. code-block:: robotframework

            Create Form
            Add Radio Button   element_id=drone  buttons=Jim,Robert  default=Robert

        """
        if not isinstance(options, list):
            options = options.split(",")
        element = {
            "type": "radiobutton",
            "id": element_id,
            "options": options,
        }
        if default is not None:
            element["default"] = default
        self.custom_form["form"].append(element)

    def add_checkbox(
        self, label: str, element_id: str, options: str, default: str = None
    ) -> None:
        """Add checkbox element

        :param label: check box element label
        :param element_id: check box element identifier
        :param options: values for the check box
        :param default: check box selected value, defaults to None

        Example:

        .. code-block:: robotframework

            Create Form
            Add Checkbox    label=Select your colors
            ...             element_id=colors
            ...             options=green,red,blue,yellow
            ...             default=blue

        """
        if not isinstance(options, list):
            options = options.split(",")
        element = {
            "type": "checkbox",
            "label": label,
            "id": element_id,
            "options": options,
        }
        if default is not None:
            element["default"] = default
        self.custom_form["form"].append(element)

    def add_textarea(
        self, name: str, rows: int = 5, cols: int = 40, default: str = None
    ) -> None:
        """Add textarea element

        :param name: textarea element name
        :param rows: number of rows for the area, defaults to 5
        :param cols: numnber of columns for the area, defaults to 40
        :param default: prefilled text for the area, defaults to None

        Example:

        .. code-block:: robotframework

            Create Form
            Add Textarea       name=feedback  default=enter feedback here
            Add Textarea       name=texts  rows=40   cols=80

        """
        element = {
            "type": "textarea",
            "name": name,
            "rows": rows,
            "cols": cols,
        }
        if default is not None:
            element["default"] = default
        self.custom_form["form"].append(element)

    def add_text(self, value: str) -> None:
        """Add text paragraph element

        :param value: text for the element

        Example.

        .. code-block:: robotframework

            Create Form
            Add Text       ${form_guidance_text}

        """
        element = {
            "type": "text",
            "value": value,
        }
        self.custom_form["form"].append(element)

    def request_response(
        self,
        formspec: str = None,
        window_width: int = 600,
        window_height: int = 1000,
        timeout: Optional[int] = None,
    ) -> Dict:
        """Start server and show form. Waits for user response.

        :param formspec: form json specification file, defaults to None
        :param window_width: window width in pixels, defaults to 600
        :param window_height: window height in pixels, defaults to 1000
        :param timeout: optional time to wait for response, in seconds
        :return: form response

        Example:

        .. code-block:: robotframework

            Create Form    ${CURDIR}/${/}myform.json
            &{response}    Request Response

        """
        self._start_server_thread()

        if self.custom_form is None:
            self.create_form("Requesting response")

        if formspec:
            formdata = open(formspec, "rb")
        else:
            formdata = json.dumps(self.custom_form)

        for attempt in count():
            try:
                response = requests.post(
                    f"{self.server_address}/formspec",
                    data=formdata,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                    timeout=5,
                )
                response.raise_for_status()
                break
            except Exception as exc:  # pylint: disable=broad-except
                if not self.thread.is_alive() or attempt >= 5:
                    raise RuntimeError("Failed to start input server") from exc
                time.sleep(1)

        return self._wait_response(window_width, window_height, timeout)

    def _wait_response(
        self, window_width: int, window_height: int, timeout: Optional[int]
    ) -> Dict:
        """Open a browser to the created form and wait for the user
        to submit it.
        """
        browser = Selenium()

        def is_browser_open():
            try:
                return bool(browser.driver.current_window_handle)
            except Exception:  # pylint: disable=broad-except
                return False

        try:
            browser.open_available_browser(self.server_address)
            browser.set_window_size(window_width, window_height)

            start_time = time.time()
            while True:
                response = requests.get(
                    f"{self.server_address}/requestresponse",
                    headers={"Prefer": "wait=120"},
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code != 304:
                    response.raise_for_status()
                elif not is_browser_open():
                    raise RuntimeError("Browser closed by user")
                elif timeout and time.time() > start_time + int(timeout):
                    raise RuntimeError("No response within timeout")
                else:
                    time.sleep(1)
        finally:
            browser.close_browser()
