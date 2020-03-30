import logging
from pathlib import Path

from fpdf import FPDF, HTMLMixin


class PDF(FPDF, HTMLMixin):
    """RPA Framework library for PDF management.
    """

    def __init__(self, pages=1, outdir="."):
        FPDF.__init__(self)
        HTMLMixin.__init__(self)
        self.logger = logging.getLogger(__name__)
        self.add_pages(pages)
        self.output_directory = Path(outdir)

    def add_pages(self, pages=1):
        """Adds pages into PDF documents

        :param pages: number of pages to add, defaults to 1
        """
        for _ in range(pages):
            self.add_page()

    def template_html_to_pdf(self, template, filename, variables=None):
        """Use HTML template file to generate PDF file.

        :param template: filepath to HTML template
        :param filename: filepath where to save PDF document
        :param variables: dictionary of variables to fill into template, defaults to {}
        """
        variables = variables or {}

        html = ""
        with open(template, "r") as templatefile:
            html = templatefile.read()
            for key, value in variables.items():
                html = html.replace("{{" + key + "}}", str(value))

        self.write_html(html)
        self.output(self.output_directory / filename)
        self.__init__()
