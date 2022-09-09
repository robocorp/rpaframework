import mimetypes
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
        region: str,
        processor_id: str,
        file_path: str,
        mime_type: str = None,
    ):
        """_summary_

        :param project_id: _description_
        :param region: _description_
        :param processor_id: _description_
        :param file_path: _description_
        :param mime_type: _description_
        :return: _description_
        """
        name = self.service.processor_path(project_id, region, processor_id)

        # Read the file into memory
        with open(file_path, "rb") as binary:
            binary_content = binary.read()

        mime = mime_type or mimetypes.guess_type(file_path)[0]
        self.logger.info(f"Processing document '{file_path}' with mimetype '{mime}'")
        # Load Binary Data into Document AI RawDocument Object
        raw_document = documentai.RawDocument(content=binary_content, mime_type=mime)

        # Configure the process request
        request = documentai.ProcessRequest(name=name, raw_document=raw_document)

        result = self.service.process_document(request=request)

        # For a full list of Document object attributes, please reference this page:
        # https://cloud.google.com/python/docs/reference/documentai/latest/google.cloud.documentai_v1.types.Document
        document = result.document
        return document

    @keyword(tags=["document ai"])
    def get_document_entities(self, document):
        """_summary_

        :param document: _description_
        :return: _description_
        """
        entities = []
        for ent in document.entities:
            entities.append(
                {
                    "id": ent.id,
                    "type": ent.type,
                    "text": ent.mention_text,
                }
            )
        return entities

    @keyword(tags=["document ai"])
    def list_processors(self, project_id: str, region: str):
        """List document AI processors.

        Requires `documentai.processors.list` permission.

        :param project_id: _description_
        :param region: _description_
        :return: _description_
        """
        parent_value = f"projects/{project_id}/locations/{region}"
        # Initialize request argument(s)
        request = documentai.ListProcessorsRequest(
            parent=parent_value,
        )

        # Make the request
        page_result = self.service.list_processors(request=request)
        return page_result
