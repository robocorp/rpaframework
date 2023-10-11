"""Custom error types used by the invocations package"""
from invoke import Context, ParseError


class RpaInvokeError(Exception):
    """Unspecified error from rpaframework invocations."""

    pass


class WrongBranchError(RpaInvokeError, ParseError):
    """Raised when an operation is attempted on the incorrect git
    branch.
    """

    def __init__(
        self, current_branch: str, expected_branch: str, context: Context = None
    ) -> None:
        self.current_branch = current_branch
        self.expected_branch = expected_branch
        self.message = f"On branch '{self.current_branch}' but expected branch '{self.expected_branch}'"
        super().__init__(self.message, context=context)
