from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import logging
import os
from pathlib import Path
import requests
from socketserver import ThreadingMixIn
import shutil
import tempfile
import threading
import time

from json import JSONDecodeError
from urllib.parse import urlparse

from RPA.Browser import Browser
from collections import OrderedDict


LOGGER = logging.getLogger(__name__)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def log_request(self, code):
        pass

    def _set_headers(self, headertype="json"):
        self.send_response(200)
        if headertype == "json":
            self.send_header("Content-type", "application/json")
        elif headertype == "html":
            self.send_header("Content-type", "text/html")
        self.end_headers()

    def import_styles(self):
        inline_styles = "<head><style>"
        with open("styles.css", "r") as styles:
            inline_styles += styles.read()
        inline_styles += "</style></head>"
        return inline_styles

    def create_form(self, message):
        has_submit = False
        formhtml = self.import_styles()
        formhtml += '<form action="formresponsehandling">'
        for item in message["form"]:
            if item["type"] == "textinput":
                formhtml += (
                    f"<label for=\"{item['name']}\">{item['label']}</label><br>"
                    f"<input type=\"text\" name=\"{item['name']}\"><br>"
                )
            elif item["type"] == "radiobutton":
                if "label" in item:
                    formhtml += f"<p>{item['label']}</p>"
                for option in item["options"]:
                    checkedvalue = ""
                    if "default" in item and item["default"] == option:
                        checkedvalue = " checked"
                    formhtml += f"""<input type=\"radio\" id=\"{option}\" name=\"{item['id']}\" value="{option}"{checkedvalue}>
                                        <label for=\"{option}\">{option}</label><br>"""
            elif item["type"] == "checkbox":
                if "label" in item:
                    formhtml += f"<p>{item['label']}</p>"
                idx = 1
                for option in item["options"]:
                    formhtml += f"""<input type=\"checkbox\" id=\"{item['id']}{idx}\" name=\"{item['id']}{idx}\" value="{option}">
                                        <label for=\"{item['id']}{idx}\">{option}</label><br>"""
                    idx += 1
            elif item["type"] == "title":
                formhtml += f"<h3>{item['value']}</h3>"
            elif item["type"] == "text":
                formhtml += f"<p>{item['value']}</p>"
            elif item["type"] == "textarea":
                defaulttext = item["default"] if "default" in item else ""
                formhtml += f"<textarea name=\"{item['name']}\" rows=\"{item['rows']}\" cols=\"{item['cols']}\">{defaulttext}</textarea><br>"
            elif item["type"] == "dropdown":
                formhtml += (
                    f"<label for=\"{item['id']}\">{item['label']}</label><br>"
                    f"<select name=\"{item['id']}\" name=\"{item['id']}\"><br>"
                )
                for option in item["options"]:
                    selected = ""
                    if "default" in item and item["default"] == option:
                        selected = " selected"
                    formhtml += f'<option name="{option}"{selected}>{option}</option>'
                formhtml += "</select><br>"
            elif item["type"] == "submit":
                for button in item["buttons"]:
                    formhtml += f"<input type=\"submit\" name=\"{item['name']}\" value=\"{button}\">"
                formhtml += "<br>"
                has_submit = True
        if not has_submit:
            formhtml += "<input type='submit' value='Submit'>"
        formhtml += "</form></body>"
        with open("form.html", "w") as f:
            f.write(formhtml)

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_POST(self):
        if "formspec" in self.path:
            # read the message and convert it into a python dictionary
            length = int(self.headers.get("content-length"))
            message = json.loads(self.rfile.read(length), object_pairs_hook=OrderedDict)
            self.create_form(message)
            self._set_headers()
            return
        else:
            self.send_response(404)
            self.end_headers()
            return

    def do_GET(self):
        if self.path.endswith("favicon.ico"):
            return
        if "formresponsehandling" in self.path:
            query = urlparse(self.path).query
            self.server.formresponse = (
                dict(qc.split("=") for qc in query.split("&")) if query else None
            )
            self._set_headers("html")
            return
        elif self.path.endswith("requestresponse"):
            if self.server.formresponse:
                self._set_headers("json")
                self.wfile.write(
                    json.dumps(self.server.formresponse).encode(encoding="utf-8")
                )
                self.server.formresponse = None
                return
            else:
                self.send_response(304)
                self.end_headers()
                return
        elif self.path.endswith(".html"):
            if self.path == "/":
                filename = "./index.html"
            else:
                filename = "./" + self.path
            self._set_headers("html")
            with open(filename, "rb") as fh:
                html = fh.read()
                # html = bytes(html, 'utf8')
                self.wfile.write(html)
            return
        else:
            self.send_response(404)
            self.end_headers()
            return


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def start_server_cmd(directory, port=8000):
    LOGGER.info("starting server at port=%s" % port)
    server = HTTPServer(("", port), Handler)
    server.formresponse = None
    server.workdir = directory
    server.serve_forever()


class Dialog:
    """[summary]"""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.server_address = None
        self.server = None
        self.workdir = None

    def start_attended_server(self, port=8105):
        if self.server is None:
            self.workdir = tempfile.mkdtemp(suffix="_dialog_server_workdir")
            shutil.copyfile(
                "includes/dialog_styles.css", Path(self.workdir) / "styles.css"
            )
            os.chdir(self.workdir)
            self.server_address = f"http://localhost:{port}"
            self.server = threading.Thread(
                name="daemon_server", target=start_server_cmd, args=(self.workdir, port)
            )
            self.server.setDaemon(True)
            self.server.start()

    def stop_attended_server(self):

        if self.server is not None and self.workdir:
            shutil.rmtree(self.workdir)

    def create_form(self, title: str = None):
        self.custom_form = OrderedDict()
        self.custom_form["form"] = list()
        if title:
            self.add_title(title)

    def add_title(self, title):
        element = {"type": "title", "value": title}
        self.custom_form["form"].append(element)

    def add_text_input(self, label, name):
        element = {"type": "textinput", "label": label, "name": name}
        self.custom_form["form"].append(element)

    def add_dropdown(self, label, id, options, default=None):
        if not isinstance(options, list):
            options = options.split(",")
        element = {"type": "dropdown", "label": label, "id": id, "options": options}
        if default:
            element["default"] = default
        self.custom_form["form"].append(element)

    def add_submit(self, name, buttons):
        if not isinstance(buttons, list):
            buttons = buttons.split(",")
        element = {"type": "submit", "name": name, "buttons": buttons}
        self.custom_form["form"].append(element)

    def request_response(self, formspec=None):
        self.start_attended_server()
        if formspec:
            formdata = open(formspec, "rb")
        else:
            formdata = json.dumps(self.custom_form)
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        requests.post(
            f"{self.server_address}/formspec",
            data=formdata,
            headers=headers,
        )
        br = Browser()
        # br.open_available_browser(f"{self.server_address}/form.html")
        br.open_chrome_as_app(f"{self.server_address}/form.html")
        br.set_window_size(600, 1000)

        headers = {"Prefer": "wait=120"}
        response_json = None
        # etag = None
        while True:
            # if etag:
            #    headers['If-None-Match'] = etag
            headers["If-None-Match"] = "2434432243"
            response = requests.get(
                f"{self.server_address}/requestresponse", headers=headers
            )
            # etag = response.headers.get("ETag")
            if response.status_code == 200:
                try:
                    response_json = response.json()
                    break
                except JSONDecodeError:
                    pass
            elif response.status_code != 304:
                # back off if the server is throwing errors
                time.sleep(60)
                continue
            time.sleep(1)

        br.close_browser()
        return response_json
