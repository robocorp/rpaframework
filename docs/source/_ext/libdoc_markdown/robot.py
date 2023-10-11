from robot.utils.htmlformatters import (
    HtmlFormatter,
    LinkFormatter as HtmlLinkFormatter,
    LineFormatter as HtmlLineFormatter,
    RulerFormatter as HtmlRulerFormatter,
    HeaderFormatter as HtmlHeaderFormatter,
    ParagraphFormatter as HtmlParagraphFormatter,
    TableFormatter as HtmlTableFormatter,
    PreformattedFormatter as HtmlPreformattedFormatter,
    ListFormatter as HtmlListFormatter,
)


class LinkFormatter(HtmlLinkFormatter):
    def _get_link(self, href, content=None):
        return "`%s <%s>`_" % (content or href, self._quot(href))


class LineFormatter(HtmlLineFormatter):
    def __init__(self):
        super().__init__()
        self._formatters = [
            ("*", self._format_bold),
            ("_", self._format_italic),
            ("``", self._format_code),
            ("", LinkFormatter().format_link),
        ]

    def _format_bold(self, line):
        return self._bold.sub("\\1**\\3**", line)

    def _format_italic(self, line):
        return self._italic.sub("\\1*\\3*", line)

    def _format_code(self, line):
        return self._code.sub("\\1``\\3``", line)


class RulerFormatter(HtmlRulerFormatter):
    def format_line(self, line):
        return "----"


class HeaderFormatter(HtmlHeaderFormatter):
    def format_line(self, line):
        # NB: Using rST structural elements shouldn't end up in docstrings,
        #     let's just use bold here instead
        _, text = self.match(line).groups()
        return f"\n**{text}**\n"


class ParagraphFormatter(HtmlParagraphFormatter):
    _format_line = LineFormatter().format

    def format(self, lines):
        paragraph = self._format_line(" ".join(lines))
        return f"\n{paragraph}\n"


class TableFormatter(HtmlTableFormatter):
    _format_cell_content = LineFormatter().format

    def _format_table(self, rows):
        if not rows:
            return ""

        has_heading = False
        widths = []

        for row_idx in range(len(rows)):
            row = rows[row_idx]

            for column_idx in range(len(row)):
                cell = row[column_idx]

                if row_idx == 0 and cell.startswith("=") and cell.endswith("="):
                    cell = cell[1:-1].strip()
                    has_heading = True

                cell = self._format_cell_content(cell)
                row[column_idx] = cell

                if len(widths) <= column_idx:
                    widths.append(len(cell))
                else:
                    widths[column_idx] = max(len(cell), widths[column_idx])

        table = []
        delimiter = ["=" * width for width in widths]

        def add_row(row):
            table.append(
                " ".join(cell.ljust(width) for cell, width in zip(row, widths))
            )

        add_row(delimiter)
        if has_heading:
            add_row(rows.pop(0))
        else:
            add_row([""] * len(widths))
        add_row(delimiter)
        for row in rows:
            add_row(row)
        add_row(delimiter)

        return "\n".join(table)


class PreformattedFormatter(HtmlPreformattedFormatter):
    _format_line = LineFormatter().format

    def format(self, lines):
        lines = ["   {}".format(self._format_line(line[2:])) for line in lines]
        return "\n".join(["::", "", *lines])


class ListFormatter(HtmlListFormatter):
    _format_item = LineFormatter().format

    def format(self, lines):
        items = []
        for line in self._combine_lines(lines):
            item = self._format_item(line)
            items.append(f"- {item}")

        return "\n".join([""] + items + [""])


class RstFormatter(HtmlFormatter):
    def __init__(self):
        super().__init__()
        self._formatters = [
            TableFormatter(),
            PreformattedFormatter(),
            ListFormatter(),
            HeaderFormatter(),
            RulerFormatter(),
        ]
        self._formatters.append(ParagraphFormatter(self._formatters[:]))
