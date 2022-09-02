from typing import Optional
from google.api_core.client_options import ClientOptions
from google.cloud import documentai_v1 as documentai

from . import LibraryContext, keyword


class DocumentAIKeywords(LibraryContext):
    """Keywords for Google Cloud Document AI API"""

    def __init__(self, ctx):
        super().__init__(ctx)
        self.service = None

    @keyword(tags=["init", "document ai"])
    def init_document_ai(
        self,
        service_account: Optional[str] = None,
        region: str = "us",
        use_robocorp_vault: Optional[bool] = None,
        token_file: str = None,
    ) -> None:
        """Initialize Google Cloud Document AI client

        :param service_account: file path to service account file
        :param region: region of the service
        :param use_robocorp_vault: use credentials in `Robocorp Vault`
        :param token_file: file path to token file
        """
        kwargs = {}
        if not region:
            raise ValueError("Parameter 'region' needs to point to a service region")
        if region.lower() != "us":
            opts = ClientOptions(
                api_endpoint=f"{region.lower()}-documentai.googleapis.com"
            )
            kwargs["client_options"] = opts
        self.logger.info(f"Using Document AI from {region} region")
        self.service = self.init_service_with_object(
            documentai.DocumentProcessorServiceClient,
            service_account,
            use_robocorp_vault,
            token_file,
            **kwargs,
        )

    @keyword(tags=["document ai"])
    def process_document(
        self,
        project_id: str,
        location: str,
        processor_id: str,
        file_path: str,
        mime_type: str,
    ):
        name = self.service.processor_path(project_id, location, processor_id)

        # Read the file into memory
        with open(file_path, "rb") as image:
            image_content = image.read()

        # Load Binary Data into Document AI RawDocument Object
        raw_document = documentai.RawDocument(
            content=image_content, mime_type=mime_type
        )

        # Configure the process request
        request = documentai.ProcessRequest(name=name, raw_document=raw_document)

        result = self.service.process_document(request=request)

        # For a full list of Document object attributes, please reference this page:
        # https://cloud.google.com/python/docs/reference/documentai/latest/google.cloud.documentai_v1.types.Document
        document = result.document

        return document
