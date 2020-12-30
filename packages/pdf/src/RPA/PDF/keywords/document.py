from RPA.PDF.keywords import (
    LibraryContext,
    keyword,
)


class DocumentKeywords(LibraryContext):
    """Keywords for basic PDF operations"""

    @keyword
    def add_pages(self, pages: int = 1) -> None:
        """Adds pages into PDF documents.

        :param pages: number of pages to add, defaults to 1
        """
        for _ in range(int(pages)):
            self.add_page()

    @keyword
    def html_to_pdf(
        self,
        content: str = None,
        filename: str = None,
        variables: dict = None,
        create_dirs: bool = True,
        exists_ok: bool = True,
    ) -> None:
        """Use HTML content to generate PDF file.

        :param content: HTML content
        :param filename: filepath where to save PDF document
        :param variables: dictionary of variables to fill into template, defaults to {}
        :param create_dirs: directory structure is created if it is missing,
         default `True`
        :param exists_ok: file is overwritten if it exists, default `True`
        """
        pass

    @keyword
    def get_info(self, source_pdf: str = None) -> dict:
        """Get information from PDF document.

        :param source_pdf: filepath to the source pdf
        :return: dictionary of PDF information
        """
        pass
