from RPA.application import (
    BaseApplication,
    catch_com_error,
    constants,
    to_path,
    to_str_path,
)
from enum import Enum
from typing import Any


class CursorPosition(Enum):
    """Enum for moving cursor position"""

    NO_MOVE = 0
    START = 1
    END = 2


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

    def paste_from_clipboard(self) -> None:
        """Paste content from clipboard to the document's
        current cursor position."""
        self.app.Selection.Paste()

    def get_current_line(self) -> str:
        """Get the text of the current line in the document."""
        original_range = self.app.Selection.Range
        self.app.Selection.Expand(Unit=constants.wdLine)
        text = self.app.Selection.Text
        original_range.Select()
        return text

    def get_number_of_lines(self) -> int:
        """Get the number of lines in the document."""
        if self.app.Documents.Count >= 1:
            return self.app.Documents.Item(1).ComputeStatistics(
                constants.wdStatisticLines
            )
        else:
            raise AssertionError("No document is open")

    def move_to_top(self) -> None:
        """Move cursor to the top of the document."""
        self.app.Selection.HomeKey(Unit=constants.wdStory)

    def move_to_end(self) -> None:
        """Move cursor to the end of the document."""
        self.app.Selection.EndKey(Unit=constants.wdStory)

    def move_to_line_start(self) -> None:
        """Move cursor to start of the line on the current cursor position."""
        self.app.Selection.HomeKey(Unit=constants.wdLine)

    def move_to_line_end(self) -> None:
        """Move cursor to end of the line on the current cursor position."""
        self.app.Selection.EndKey(Unit=constants.wdLine)

    def move_vertically(
        self,
        lines: int = 0,
    ) -> Any:
        """Move cursor vertically from current cursor position.

        Remember that if cursor is already at the top the cursor can't
        move up and if cursor is already at the bottom the cursor can't
        move down.

        :param lines: lines to move
        """
        if lines > 0:
            self.app.Selection.MoveDown(Unit=constants.wdLine, Count=lines)
        elif lines < 0:
            self.app.Selection.MoveUp(Unit=constants.wdLine, Count=-lines)
        self.app.Selection.Select()

    def move_horizontally(
        self,
        characters: int = 0,
    ) -> Any:
        """Move cursor horizontally from current cursor position.

        Remember that if cursor is already at the start the cursor can't move
        left and if cursor is already at the end the cursor can't move right.

        :param characters: characters to move
        """
        if characters > 0:
            self.app.Selection.MoveRight(Unit=constants.wdCharacter, Count=characters)
        elif characters < 0:
            self.app.Selection.MoveLeft(Unit=constants.wdCharacter, Count=-characters)
        self.app.Selection.Select()

    def find_text(
        self,
        text: str,
        cursor_position: CursorPosition = CursorPosition.NO_MOVE,
        copy: bool = False,
    ) -> None:
        """Find text in the document.

        :param text: text to find
        :param cursor_position: where to move cursor after finding text
        :param copy: copy found text into clipboard
        :raises AssertionError: if text is not found
        """
        found = False
        content_range = None
        if self.app.Documents.Count >= 1:
            content_range = self.app.Documents.Item(1).Content
            content_range.Find.ClearFormatting()
            found = content_range.Find.Execute(FindText=text)
        else:
            raise AssertionError("No document is open")
        if not found:
            raise AssertionError(f"Text '{text}' not found in the document")
        if copy:
            content_range.Copy()
        if cursor_position != CursorPosition.NO_MOVE:
            direction = (
                constants.wdCollapseStart
                if cursor_position == CursorPosition.START
                else constants.wdCollapseEnd
            )
            content_range.Collapse(Direction=direction)

    def write_text(
        self,
        text: str,
        cursor_position: CursorPosition = CursorPosition.NO_MOVE,
        end_of_text: bool = True,
    ) -> None:
        """Writes given text at the end of the document

        :param text: string to write
        :param cursor_position: where to move cursor before writing
        :param end_of_text: if True moves cursor to the end of the text
         before writing
        """

        if end_of_text:
            self.move_to_end()

        if cursor_position != CursorPosition.NO_MOVE:
            direction = (
                constants.wdCollapseStart
                if cursor_position == CursorPosition.START
                else constants.wdCollapseEnd
            )

            self.app.Selection.Collapse(Direction=direction)

        self.app.Selection.TypeText(text)
        self.app.Selection.Select()

    def select_current_paragraph(self):
        """Select text in current active paragraph."""
        self.app.Selection.Paragraphs(1).Range.Select()

    def copy_selection_to_clipboard(self):
        """Copy current text selection to clipboard."""
        self.app.Selection.Copy()

    def select_paragraph(self, count: int = 1):
        """Select paragraph(s) from current cursor position.

        Negative `count` moves cursor up number of paragraphs and
        positive `count` moves cursor down number of paragraphs.

        :param count: number of paragraphs to select
        """
        start = self.app.Selection.Range.Start
        self.app.Selection.MoveDown(Unit=constants.wdParagraph, Count=count)
        end = self.app.Selection.Range.End
        self.app.Selection.SetRange(start, end)
