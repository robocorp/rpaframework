import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import webview  # type: ignore
from RPA.Dialogs.bridge import Bridge  # type: ignore

LOGGER = logging.getLogger(__name__)


def static() -> str:
    # NB: pywebview uses sys.argv[0] as base
    base = Path(sys.argv[0]).resolve().parent
    path = Path(__file__).resolve().parent / "static"
    return os.path.relpath(str(path), str(base))


def output(obj: Any) -> None:
    print(json.dumps(obj), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("elements")
    parser.add_argument("--title", default="Dialog")
    parser.add_argument("--width", default=480, type=int)
    parser.add_argument("--height", default=640, type=int)
    parser.add_argument("--auto_height", action="store_true")
    parser.add_argument("--on_top", action="store_true")
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()

    # Suppress useless error messages from pywebview
    logging.getLogger("pywebview").setLevel(logging.CRITICAL)

    try:
        elements = json.loads(args.elements)

        bridge = Bridge(
            elements=elements, auto_height=args.auto_height, on_top=args.on_top
        )
        window = webview.create_window(
            url=os.path.join(static(), "index.html"),
            js_api=bridge,
            resizable=True,
            text_select=True,
            background_color="#0b1025",
            title=args.title,
            width=args.width,
            height=args.height,
            on_top=True,
        )
        bridge.window = window

        LOGGER.debug("Starting dialog")
        webview.start(debug=args.debug)

        if bridge.error is not None:
            output({"error": bridge.error})
        if bridge.result is not None:
            output({"value": bridge.result})
        else:
            output({"error": "Aborted by user"})
    except Exception as err:  # pylint: disable=broad-except
        output({"error": str(err)})
    finally:
        LOGGER.debug("Dialog closed")


if __name__ == "__main__":
    main()
