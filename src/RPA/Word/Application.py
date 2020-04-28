import logging
from pathlib import Path
import platform

from RPA.core.msoffice import OfficeApplication

if platform.system() == "Windows":
    from win32com.client import constants


FILEFORMATS = {
    "DEFAULT": "wdFormatDocumentDefault",
    "PDF": "wdFormatPDF",
    "RTF": "wdFormatRTF",
    "HTML": "wdFormatHTML",
    "WORD97": "wdFormatDocument97",
    "OPENDOCUMENT": "wdFormatOpenDocumentText",
}


class Application(OfficeApplication):
    """Library for manipulating Word application."""

    def __init__(self) -> None:
        OfficeApplication.__init__(self, application_name="Word")
        self.logger = logging.getLogger(__name__)
        self.filename = None

    def open_file(self, filename: str = None) -> None:
        """Open Word document with filename.

        :param filename: Word document filepath, defaults to None
        """
        if filename is not None:
            word_filepath = str(Path(filename).resolve())
            self.logger.info("Opening document: %s", word_filepath)
            doc = self.app.Documents.Open(word_filepath, False, True, None)
            doc.Activate()
            self.app.ActiveWindow.View.ReadingLayout = False
            self.filename = word_filepath
        else:
            self.logger.warning("Filename was not given.")

    def create_new_document(self) -> None:
        """Create new document for Word application
        """
        if self.app:
            self.app.Documents.Add()

    def export_to_pdf(self, filename: str) -> None:
        """Export active document into PDF file.

        :param filename: PDF to export WORD into
        """
        absolute_filepath = str(Path(filename).resolve())
        self.app.ActiveDocument.ExportAsFixedFormat(
            OutputFileName=absolute_filepath, ExportFormat=constants.wdExportFormatPDF
        )

    def write_text(self, text: str, newline: bool = True) -> None:
        """Writes given text at the end of the document

        :param text: string to write
        :param newline: write text to newline if True, default to True
        """
        self.app.Selection.EndKey(Unit=constants.wdStory)
        if newline:
            text = f"\n{text}"
        self.app.Selection.TypeText(text)
        # self.app.ActiveDocument.Content.InsertAfter(text)

    def replace_text(self, find: str, replace: str) -> None:
        """Replace text in active document

        :param find: text to replace
        :param replace: new text
        """
        self.app.ActiveDocument.Content.Find.Execute(FindText=find, ReplaceWith=replace)

    def set_header(self, text: str) -> None:
        """Set header for the active document

        :param text: header text to set
        """
        for section in self.app.ActiveDocument.Sections:
            for header in section.Headers:
                header.Range.Text = text

    def set_footer(self, text: str) -> None:
        """Set footer for the active document

        :param text: footer text to set
        """
        for section in self.app.ActiveDocument.Sections:
            for footer in section.Footers:
                footer.Range.Text = text

    def save_document(self) -> None:
        """Save active document
        """
        # Accept all revisions
        self.app.ActiveDocument.Revisions.AcceptAll()
        # Delete all comments
        if self.app.ActiveDocument.Comments.Count >= 1:
            self.app.ActiveDocument.DeleteAllComments()
        self.app.ActiveDocument.Save()

    def save_document_as(self, filename: str, fileformat: str = None) -> None:
        """Save document with filename and optionally with given fileformat

        :param filename: where to save document
        :param fileformat: see @FILEFORMATS dictionary for possible format,
            defaults to None
        """
        absolute_filepath = str(Path(filename).resolve())
        # Accept all revisions
        self.app.ActiveDocument.Revisions.AcceptAll()
        # Delete all comments
        if self.app.ActiveDocument.Comments.Count >= 1:
            self.app.ActiveDocument.DeleteAllComments()
        self.logger.info("Saving file to absolute path: %s", absolute_filepath)
        if fileformat and fileformat.upper() in FILEFORMATS.keys():
            self.logger.debug("Saving with file format: %s", fileformat)
            format_name = FILEFORMATS[fileformat.upper()]
            format_type = getattr(constants, format_name)
            self.app.ActiveDocument.SaveAs2(
                FileName=absolute_filepath, FileFormat=format_type
            )
        else:
            self.app.ActiveDocument.SaveAs2(
                absolute_filepath, FileFormat=constants.wdFormatDocumentDefault
            )
        self.logger.info("File saved to: %s", absolute_filepath)

    def get_all_texts(self) -> str:
        """Get all texts from active document

        :return: texts
        """
        return self.app.ActiveDocument.Content.Text
