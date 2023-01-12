import mimetypes
import pickle
from typing import List, Optional

from google.api_core.client_options import ClientOptions
from google.cloud import documentai_v1 as documentai

from . import LibraryContext, keyword


class DocumentAIKeywords(LibraryContext):
    """Keywords for Google Cloud Document AI service.

    Added on **rpaframework-google** version: 6.1.1

    Google Document AI provides processors for intelligent
    document processing (IDP).

    To take Document AI into use:

        - Create Google Cloud project
        - Enable Google Cloud Document AI API for the project
        - For Document AI product page, activate desired processors
          for the project
    """

    def __init__(self, ctx):
        super().__init__(ctx)
        self.service = None

    @keyword(name="Init Document AI", tags=["init", "document ai"])
    def init_document_ai(
        self,
        service_account: Optional[str] = None,
        region: Optional[str] = "us",
        use_robocorp_vault: Optional[bool] = None,
        token_file: Optional[str] = None,
    ) -> None:
        """Initialize Google Cloud Document AI client

        :param service_account: file path to service account file
        :param region: region of the service
        :param use_robocorp_vault: use credentials in `Robocorp Vault`
        :param token_file: file path to token file

        Robot Framework example:

        .. code-block:: robotframework

            # Init using Service Account from a file
            Init Document AI   ${CURDIR}${/}service_account.json  region=eu
            # Init using OAuth token from a file and default "us" region
            Init Document AI   ${CURDIR}${/}token.json
            # Init using service account file from the Robocorp Vault
            Set Robocorp Vault
            ...         vault_name=DocumentAI
            ...         vault_secret_key=google-sa
            Init Document AI    region=eu    use_robocorp_vault=True

        Python example:

        .. code-block:: python

            GOOGLE = Google()
            GOOGLE.set_robocorp_vault("DocumentAI", "google-sa")
            GOOGLE.init_document_ai(region="eu", use_robocorp_vault=True)
        """
        kwargs = {}
        if not region:
            raise ValueError("Parameter 'region' needs to point to a service region")
        if region.lower() != "us":
            opts = ClientOptions(
                api_endpoint=f"{region.lower()}-documentai.googleapis.com"
            )
            kwargs["client_options"] = opts
        self.logger.info(f"Using Document AI from '{region.upper()}' region")
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
        mime_type: Optional[str] = None,
    ) -> documentai.Document:
        """Process document in the Google Cloud platform
        using given document processor ID within given project and
        region.

        For a full list of Document response object attributes, please reference this
        `page <https://cloud.google.com/python/docs/reference/documentai/latest/google.cloud.documentai_v1.types.Document/>`_.


        :param project_id: Google Cloud project ID
        :param region: Google Cloud region of the processor
        :param processor_id: ID of the document processor
        :param file_path: filepath of the document to process
        :param mime_type: given mime type of document (optional),
         if not given it is auto detected
        :return: processed document response object

        Robot Framework example:

        .. code-block:: robotframework

            ${document}=    Process Document
            ...    project_id=${GOOGLE_PROJECT_ID}
            ...    region=eu
            ...    processor_id=${RECEIPT_PROCESSOR_ID}
            ...    file_path=${CURDIR}${/}mydocument.pdf
            ${entities}=    Get Document Entities    ${document}
            FOR  ${ent}  IN  @{entities}
                Log To Console  Entity: ${ent}
            END
            ${languages}=    Get Document Languages    ${document}
            Log To Console    Languages: ${languages}

        Python example:

        .. code-block:: python

            document = GOOGLE.process_document(
                project_id=PROJECT_ID,
                region="eu",
                processor_id=PROCESSOR_ID,
                file_path="./files/mydocument.pdf",
            )
            entities = GOOGLE.get_document_entities(document)
            for ent in entities:
                print(ent)
            languages = GOOGLE.get_document_languages(document)
            for lang in languages:
                print(lang)
        """  # noqa: E501
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

        document = result.document
        return document

    @keyword(tags=["document ai"])
    def save_document_response(
        self, document: documentai.Document, filepath: str
    ) -> None:
        """Save ``Process Document`` response into a binary file.

        :param document: response document object
        :param filepath: target file to save binary object into

        Robot Framework example:

        .. code-block:: robotframework

            ${document}=    Process Document
            ...    project_id=101134120147
            ...    region=eu
            ...    processor_id=${RECEIPT_PROCESSOR}
            ...    file_path=${file_in}
            # save response for later
            Save Document Response  ${CURDIR}${/}google_processed.response

        Python example:

        .. code-block:: python

            document = GOOGLE.process_document(
                project_id=PROJECT_ID,
                region="eu",
                processor_id=PROCESSOR_ID,
                file_path="./files/receipt1.jpg",
            )
            GOOGLE.save_document_response(document, "receipt.response")
        """
        with open(filepath, "wb") as response_file:
            pickle.dump(document, response_file)

    @keyword(tags=["document ai"])
    def load_document_response(self, filepath: str) -> documentai.Document:
        """Loads the binary object saved by ``Save Document Response`` into
        ``documentai.Document`` format which is accessible by helper keywords.

        :param filepath: source file to read binary document object from
        :return: processed document response object

        Robot Framework example:

        .. code-block:: robotframework

            # load previously saved response
            ${document}=  Load Document Response  ${CURDIR}${/}google_processed.response
            ${entities}=  Get Document Entities  ${document}

        Python example:

        .. code-block:: python

            document = GOOGLE.load_document_response("google_doc.response")
            entities = GOOGLE.get_document_entities(document)
            for ent in entities:
                print(ent)
        """
        document = None
        with open(filepath, "rb") as response_file:
            try:
                document = pickle.load(response_file)
            except pickle.UnpicklingError as err:
                raise ValueError(
                    f"The file {filepath!r} is not 'documentai.Document' type"
                ) from err

        if not isinstance(document, documentai.Document):
            raise ValueError(
                "The file '%s' is not 'documentai.Document' type" % filepath
            )
        return document

    @keyword(tags=["document ai", "get"])
    def get_document_entities(self, document: documentai.Document) -> List:
        """Helper keyword for getting document `entities` from a ``Process Document``
        response object.

        For examples. see ``Process Document`` keyword

        :param document: the document response object
        :return: detected entities in the document response as a list
        """
        entities = []
        for ent in document.entities:
            entities.append(
                {
                    "id": ent.id,
                    "confidence": ent.confidence,
                    "page": int(ent.page_anchor.page_refs[0].page) + 1,
                    "type": ent.type_,
                    "normalized": ent.normalized_value.text,
                    "text": ent.text_anchor.content,
                }
            )
        return entities

    @keyword(tags=["document ai", "get"])
    def get_document_languages(self, document: documentai.Document) -> List:
        """Helper keyword for getting detected `languages` from a ``Process Document``
        response object.

        For examples. see ``Process Document`` keyword

        :param document: the document response object
        :return: detected languages in the document response as a list
        """
        languages = []
        for page in document.pages:
            for lang in page.detected_languages:
                languages.append(
                    {
                        "page": page.page_number,
                        "code": lang.language_code,
                        "confidence": lang.confidence,
                    }
                )
        return languages

    @keyword(tags=["document ai"])
    def list_processors(self, project_id: str, region: str) -> List:
        """List existing document AI processors from given project and region.

        Requires `documentai.processors.list` permission.

        :param project_id: Google Cloud project ID
        :param region: Google Cloud region of the processor
        :return: list of available processors as a list

        Robot Framework example:

        .. code-block:: robotframework

            @{processors}=    List Processors    ${PROJECT_ID}    eu
            FOR    ${p}    IN    @{processors}
                # name: projects/PROJECT_ID/locations/REGION/processors/PROCESSOR_ID
                Log To Console    Processor name: ${p.name}
                Log To Console    Processor type: ${p.type_}
                Log To Console    Processor display name: ${p.display_name}
            END

        Python example:

        .. code-block:: python

            processors = GOOGLE.list_processors(PROJECT_ID, "eu")
            for p in processors:
                print(f"Processor name: {p.name}")
                print(f"Processor type: {p.type_}")
                print(f"Processor name: {p.display_name}")
        """
        parent_value = self.service.common_location_path(project_id, region)
        # Initialize request argument(s)
        request = documentai.ListProcessorsRequest(
            parent=parent_value,
        )
        processor_list = self.service.list_processors(request=request)
        return processor_list
