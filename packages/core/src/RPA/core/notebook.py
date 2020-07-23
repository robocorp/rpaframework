from importlib import util
import inspect


def notebook_print(**kwargs) -> None:
    """Print Markdown formatted strings into IPython notebook
    if IPython is available.

    Valid parameters are `text`, `image`, `link` or `table`.

    :param text: string to output (can contain markdown)
    :param image: path to the image file
    :param link: path to the link
    :param table: `RPA.Table` object to print
    """
    curframe = inspect.currentframe()
    calframe = inspect.getouterframes(curframe, 2)
    keyword_name = calframe[1][3]

    output = _get_markdown(**kwargs)
    if output == "":
        return
    else:
        output += "<br>"
    if not keyword_name.startswith("<module>"):
        output = f"**KW** {keyword_name}: " + output

    ipython_module = util.find_spec("IPython")
    if ipython_module is None:
        return output
    # pylint: disable=C0415
    from IPython.display import Markdown, display  # noqa

    output += "<hr><br>"
    display(Markdown(output))


def _get_table_output(table):
    output = ""
    try:
        # pylint: disable=C0415
        from RPA.Tables import Tables, Table  # noqa

        if isinstance(table, Table):
            output = "<table>"
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
            output += "</table>"
    except ImportError:
        pass
    return output


def _get_markdown(**kwargs):
    output = ""
    for key, val in kwargs.items():
        if key == "text":
            output += val
        if key == "image":
            output += f"<img src='{val}'>"
        if key == "link":
            link_text = (val[:75] + "..") if len(val) > 75 else val
            output += f"<a href='{val}'>{link_text}</a>"
        if key == "table":
            output += _get_table_output(val)
    return output
