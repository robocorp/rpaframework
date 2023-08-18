from RPA.application import (
    BaseApplication,
    catch_com_error,
    constants,
    to_path,
    to_str_path,
)


class Application(BaseApplication):
    """`Word.Application` is a library for controlling the Word application.

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

    APP_DISPATCH = "Word.Application"
    FILEFORMATS = {
        "DEFAULT": "wdFormatDocumentDefault",
        "PDF": "wdFormatPDF",
        "RTF": "wdFormatRTF",
        "HTML": "wdFormatHTML",
        "WORD97": "wdFormatDocument97",
        "OPENDOCUMENT": "wdFormatOpenDocumentText",
    }

    def open_file(self, filename: str, read_only: bool = True) -> None:
        """Open Word document with filename.

        :param filename: Word document path
        """
        path = to_path(filename)
        if not path.is_file():
            raise FileNotFoundError(f"{str(path)!r} doesn't exist")

        state = "read-only" if read_only else "read-write"
        self.logger.info("Opening document (%s): %s", state, path)
        with catch_com_error():
            doc = self.app.Documents.Open(
                FileName=str(path),
                ConfirmConversions=False,
                ReadOnly=read_only,
                AddToRecentFiles=False,
            )

        err_msg = None
        if doc is None:
            err_msg = (
                "Got null object when opening the document, enable RDP connection if"
                " running by Control Room through a Worker service"
            )
        elif not hasattr(doc, "Activate"):
            err_msg = (
                "The document can't be activated, open it manually and dismiss any"
                " alert you may encounter first"
            )
        if err_msg:
            raise IOError(err_msg)

        doc.Activate()
        self.app.ActiveWindow.View.ReadingLayout = False

    def create_new_document(self) -> None:
        """Create new document for Word application"""
        with catch_com_error():
            self.app.Documents.Add()

    def export_to_pdf(self, filename: str) -> None:
        """Export active document into PDF file.

        :param filename: PDF to export WORD into
        """
        path = to_str_path(filename)
        with catch_com_error():
            self._active_document.ExportAsFixedFormat(
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

    def replace_text(self, find: str, replace: str) -> None:
        """Replace text in active document

        :param find: text to replace
        :param replace: new text
        """
        self._active_document.Content.Find.Execute(FindText=find, ReplaceWith=replace)

    def set_header(self, text: str) -> None:
        """Set header for the active document

        :param text: header text to set
        """
        for section in self._active_document.Sections:
            for header in section.Headers:
                header.Range.Text = text

    def set_footer(self, text: str) -> None:
        """Set footer for the active document

        :param text: footer text to set
        """
        for section in self._active_document.Sections:
            for footer in section.Footers:
                footer.Range.Text = text

    def save_document(self) -> None:
        """Save active document"""
        # Accept all revisions
        self._active_document.Revisions.AcceptAll()
        # Delete all comments
        if self._active_document.Comments.Count >= 1:
            self._active_document.DeleteAllComments()

        self._active_document.Save()

    def save_document_as(self, filename: str, fileformat: str = None) -> None:
        """Save document with filename and optionally with given fileformat

        :param filename: where to save document
        :param fileformat: see @FILEFORMATS dictionary for possible format,
            defaults to None
        """
        path = to_str_path(filename)

        # Accept all revisions
        self._active_document.Revisions.AcceptAll()
        # Delete all comments
        if self._active_document.Comments.Count >= 1:
            self._active_document.DeleteAllComments()

        if fileformat and fileformat.upper() in self.FILEFORMATS:
            self.logger.debug("Saving with file format: %s", fileformat)
            format_name = self.FILEFORMATS[fileformat.upper()]
            format_type = getattr(constants, format_name)
        else:
            format_type = constants.wdFormatDocumentDefault

        try:
            self._active_document.SaveAs2(path, FileFormat=format_type)
        except AttributeError:
            self._active_document.SaveAs(path, FileFormat=format_type)

        self.logger.info("File saved to: %s", path)

    def get_all_texts(self) -> str:
        """Get all texts from active document

        :return: texts
        """
        return self._active_document.Content.Text
