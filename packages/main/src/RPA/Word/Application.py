import logging
from pathlib import Path
import platform

if platform.system() == "Windows":
    import win32com.client
    from win32com.client import constants
else:
    logging.getLogger(__name__).warning(
        "RPA.Word.Application library works only on Windows platform"
    )


FILEFORMATS = {
    "DEFAULT": "wdFormatDocumentDefault",
    "PDF": "wdFormatPDF",
    "RTF": "wdFormatRTF",
    "HTML": "wdFormatHTML",
    "WORD97": "wdFormatDocument97",
    "OPENDOCUMENT": "wdFormatOpenDocumentText",
}


class Application:
    """`Word.Application` is a library for controlling a Word application.

    *Note*. Library works only Windows platform.

    **Examples**

    **Robot Framework**

    .. code-block:: robotframework

        *** Settings ***
        Library                 RPA.Word.Application
        Task Setup              Open Application
        Suite Teardown          Quit Application

        *** Tasks ***
        Open existing file
            Open File           old.docx
            Write Text          Extra Line Text
            Write Text          Another Extra Line of Text
            Save Document AS    ${CURDIR}${/}new.docx
            ${texts}=           Get all Texts
            Close Document

    **Python**

    .. code-block:: python

        from RPA.Word.Application import Application

        app = Application()
        app.open_application()
        app.open_file('old.docx')
        app.write_text('Extra Line Text')
        app.save_document_as('new.docx')
        app.quit_application()
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.app = None
        self.filename = None

        if platform.system() != "Windows":
            self.logger.warning(
                "Word application library requires Windows dependencies to work."
            )

    def open_application(
        self, visible: bool = False, display_alerts: bool = False
    ) -> None:
        """Open the Word application.

        :param visible: show window after opening
        :param display_alerts: show alert popups
        """
        self.app = win32com.client.gencache.EnsureDispatch("Word.Application")

        if hasattr(self.app, "Visible"):
            self.app.Visible = visible

        # show eg. file overwrite warning or not
        if hasattr(self.app, "DisplayAlerts"):
            self.app.DisplayAlerts = display_alerts

    def close_document(self, save_changes: bool = False) -> None:
        """Close the active document (if open)."""
        if self.app is not None:
            self.app.ActiveDocument.Close(save_changes)

    def quit_application(self, save_changes: bool = False) -> None:
        """Quit the application."""
        if self.app is not None:
            self.close_document(save_changes)
            self.app.Quit()
            self.app = None

    def open_file(self, filename: str, read_only: bool = True) -> None:
        """Open Word document with filename.

        :param filename: Word document path
        """
        path = str(Path(filename).resolve())
        self.logger.info("Opening document: %s", path)

        doc = self.app.Documents.Open(
            FileName=path,
            ConfirmConversions=False,
            ReadOnly=read_only,
            AddToRecentFiles=False,
        )

        doc.Activate()
        self.app.ActiveWindow.View.ReadingLayout = False
        self.filename = path

    def create_new_document(self) -> None:
        """Create new document for Word application"""
        if self.app:
            self.app.Documents.Add()

    def export_to_pdf(self, filename: str) -> None:
        """Export active document into PDF file.

        :param filename: PDF to export WORD into
        """
        path = str(Path(filename).resolve())
        self.app.ActiveDocument.ExportAsFixedFormat(
            OutputFileName=path, ExportFormat=constants.wdExportFormatPDF
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
        """Save active document"""
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
        path = str(Path(filename).resolve())

        # Accept all revisions
        self.app.ActiveDocument.Revisions.AcceptAll()
        # Delete all comments
        if self.app.ActiveDocument.Comments.Count >= 1:
            self.app.ActiveDocument.DeleteAllComments()

        if fileformat and fileformat.upper() in FILEFORMATS.keys():
            self.logger.debug("Saving with file format: %s", fileformat)
            format_name = FILEFORMATS[fileformat.upper()]
            format_type = getattr(constants, format_name)
        else:
            format_type = constants.wdFormatDocumentDefault

        try:
            self.app.ActiveDocument.SaveAs2(path, FileFormat=format_type)
        except AttributeError:
            self.app.ActiveDocument.SaveAs(path, FileFormat=format_type)

        self.logger.info("File saved to: %s", path)

    def get_all_texts(self) -> str:
        """Get all texts from active document

        :return: texts
        """
        return self.app.ActiveDocument.Content.Text
