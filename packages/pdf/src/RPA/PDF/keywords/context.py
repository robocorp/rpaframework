
class ElementNotFound(ValueError):
    """No matching elements were found."""


class MultipleElementsFound(ValueError):
    """Multiple matching elements were found, but only one was expected."""


class TimeoutException(ValueError):
    """Timeout reached while waiting for condition."""


class LibraryContext:
    """Shared context for all keyword libraries."""

    def __init__(self, ctx):
        self.ctx = ctx

    @property
    def logger(self):
        return self.ctx.logger

    @property
    def rpa_pdf_document(self):
        return self.ctx.rpa_pdf_document

    @rpa_pdf_document.setter
    def rpa_pdf_document(self, value):
        self.ctx.rpa_pdf_document = value
