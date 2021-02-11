import logging
from robotlibcore import DynamicCore

from RPA.PDF.keywords import DocumentKeywords, FinderKeywords, ModelKeywords


class PDF(DynamicCore):
    """`PDF` is a library for managing PDF documents.

    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.fileobjects = {}
        self.active_pdf_document = None

        # Register keyword libraries to LibCore
        libraries = [
            DocumentKeywords(self),
            FinderKeywords(self),
            ModelKeywords(self),
        ]
        super().__init__(libraries)

        # TODO: how to use this RPA.main keyword library
        # listener = RobotLogListener()
        # listener.register_protected_keywords(["RPA.PDF.decrypt"])
