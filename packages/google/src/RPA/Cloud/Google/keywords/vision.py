from apiclient import discovery
from google.oauth2 import service_account
import os
from typing import (
    List,
    Union,
)
from RPA.Cloud.Google.keywords import (
    LibraryContext,
    keyword,
)


class VisionKeywords(LibraryContext):
    """Keywords for Google Sheets operations"""

    def __init__(self, ctx):
        super().__init__(ctx)
        self.service = None