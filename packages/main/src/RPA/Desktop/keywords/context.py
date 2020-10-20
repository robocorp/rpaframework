class LibraryContext:
    """Shared context for all keyword libraries."""

    def __init__(self, ctx):
        self.ctx = ctx

    @property
    def logger(self):
        return self.ctx.logger

    def find_element(self, *args, **kwargs):
        return self.ctx.find_element(*args, **kwargs)
