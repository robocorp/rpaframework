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
    def active_pdf_document(self):
        return self.ctx.active_pdf_document

    @active_pdf_document.setter
    def active_pdf_document(self, value):
        self.ctx.active_pdf_document = value
