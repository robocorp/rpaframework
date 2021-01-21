from functools import wraps
from importlib import util
import inspect
import os
from typing import Any

IPYTHON_AVAILABLE = False

ipython_module = util.find_spec("IPython")
if ipython_module:
    # pylint: disable=C0415
    from IPython.display import (  # noqa
        Audio,
        display,
        FileLink,
        FileLinks,
        Image,
        JSON,
        Markdown,
        Video,
    )

    IPYTHON_AVAILABLE = True


def _get_caller_prefix(calframe):
    keyword_name = (
        calframe[1][3] if calframe[1][3] not in ["<module>", "<lambda>"] else None
    )
    if keyword_name:
        keyword_name = keyword_name.replace("_", " ").title()
        return f"Output from **{keyword_name}**"
    return ""


def print_precheck(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not IPYTHON_AVAILABLE:
            return None
        output_level = os.getenv("RPA_NOTEBOOK_OUTPUT_LEVEL", "1")
        if output_level == "0":
            return None
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        prefix = _get_caller_prefix(calframe)
        if prefix != "":
            display(Markdown(prefix))
        return f(*args, **kwargs)

    return wrapper


@print_precheck
def notebook_print(arg=None, **kwargs) -> Any:
    """Display IPython Markdown object in the notebook

    Valid parameters are `text`, `image`, `link` or `table`.

    :param text: string to output (can contain markdown)
    :param image: path to the image file
    :param link: path to the link
    :param table: `RPA.Table` object to print
    """
    if arg and "text" in kwargs.keys():
        kwargs["text"] = f"{arg} {kwargs['text']}"
    elif arg:
        kwargs["text"] = arg
    output = _get_markdown(**kwargs)

    if output:
        display(Markdown(output))


@print_precheck
def notebook_file(filepath):
    """Display IPython FileLink object in the notebook

    :param filepath: location of the file
    """
    if filepath:
        display(FileLink(filepath))


@print_precheck
def notebook_dir(directory, recursive=False):
    """Display IPython FileLinks object in the notebook

    :param directory: location of the directory
    :param recursive: if all subdirectories should be shown also, defaults to False
    """
    if directory:
        display(FileLinks(directory, recursive=recursive))


@print_precheck
def notebook_table(table: Any, count: int = 20, columns=None, index=None):
    """Display RPA.Table or RPA.Table shaped data as IPython Markdown object in the notebook

    :param table: `RPA.Table` object to print
    :param count: How many rows of table to print
    :param columns: Names / headers of the table columns
    :param index: List of indices for table rows
    """
    # pylint: disable=C0415,E0611
    from RPA.Tables import Table, Tables  # noqa

    table = Table(table, columns, index)
    if count:
        table = Tables().table_head(table, count=count)
    output = _get_table_output(table)
    if output:
        display(Markdown(output))


@print_precheck
def notebook_image(image):
    """Display IPython Image object in the notebook

    :param image: path to the image file
    """
    if image:
        display(Image(image))


@print_precheck
def notebook_video(video):
    """Display IPython Video object in the notebook

    :param video: path to the video file
    """
    if video:
        display(Video(video))


@print_precheck
def notebook_audio(audio):
    """Display IPython Audio object in the notebook

    :param audio: path to the audio file
    """
    if audio:
        display(Audio(filename=audio))


@print_precheck
def notebook_json(json_object):
    """Display IPython JSON object in the notebook

    :param json_object: item to show
    """
    if json_object:
        display(JSON(json_object))


def _get_table_output(table):
    # pylint: disable=C0415,E0611
    from RPA.Tables import Tables, Table  # noqa

    output = ""
    try:
        if isinstance(table, Table):
            output = "<table class='rpafw-notebook-table'>"
            header = Tables().table_head(table, count=1)
            for row in header:
                output += "<tr>"
                for h, _ in row.items():
                    output += f"<th>{h}</th>"
                output += "</tr>"
            for row in table:
                output += "<tr>"
                for _, cell in row.items():
                    output += f"<td>{cell}</td>"
                output += "</tr>"
            output += "</table><br>"
    except ImportError:
        pass
    return None if output == "" else output


def _get_markdown(**kwargs):
    output = ""
    for key, val in kwargs.items():
        if key == "text":
            output += f"<span class='rpafw-notebook-text'>{val}</span><br>"
        if key == "image":
            output += f"<img class='rpafw-notebook-image' src='{val}'><br>"
        if key == "link":
            link_text = (val[:75] + "..") if len(val) > 75 else val
            output += f"<a class='rpafw-notebook-link' href='{val}'>{link_text}</a><br>"
        if key == "table":
            output += _get_table_output(val)
    return None if output == "" else output
