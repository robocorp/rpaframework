from google.cloud import language_v1
from google.cloud.language_v1 import enums


from RPA.Cloud.Google.keywords import (
    LibraryContext,
    keyword,
)


class NaturalLanguageKeywords(LibraryContext):
    """Keywords for Google Cloud Natural Language API"""

    def __init__(self, ctx):
        super().__init__(ctx)
        self.service = None

    @keyword
    def init_natural_language(
        self, service_account: str = None, use_robocloud_vault: bool = False
    ) -> None:
        """Initialize Google Cloud Natural Language client

        :param service_credentials_file: filepath to credentials JSON
        :param use_robocloud_vault: use json stored into `Robocloud Vault`
        """
        self.init_service_with_object(
            language_v1.LanguageServiceClient,
            service_account,
            use_robocloud_vault,
        )

    @keyword
    def analyze_sentiment(
        self, text_file: str, file_type: str = "text", json_file: str = None, lang=None
    ) -> dict:
        """Analyze sentiment in a text file

        :param text_file: source text file
        :param json_file: json target to save result, defaults to None
        :param lang: language code of the source, defaults to None
        :return: analysis response
        """
        with open(text_file, "r") as f:
            text_content = f.read()
        # Available types: PLAIN_TEXT, HTML
        if file_type == "text":
            type_ = enums.Document.Type.PLAIN_TEXT
        else:
            type_ = enums.Document.Type.HTML
        document = {"content": text_content, "type": type_}
        # Optional. If not specified, the language is automatically detected.
        # For list of supported languages:
        # https://cloud.google.com/natural-language/docs/languages
        if lang is not None:
            document["language"] = lang
        # Available values: NONE, UTF8, UTF16, UTF32
        encoding_type = enums.EncodingType.UTF8
        response = self.service.analyze_sentiment(document, encoding_type=encoding_type)
        self.write_json(json_file, response)
        return response

    @keyword
    def classify_text(self, text_file, json_file, lang=None):
        """Classify text

        :param text_file: source text file
        :param json_file: json target to save result, defaults to None
        :param lang: language code of the source, defaults to None
        :return: classify response
        """
        with open(text_file, "r") as f:
            text_content = f.read()
        # Available types: PLAIN_TEXT, HTML
        type_ = enums.Document.Type.PLAIN_TEXT
        document = {"content": text_content, "type": type_}
        # Optional. If not specified, the language is automatically detected.
        # For list of supported languages:
        # https://cloud.google.com/natural-language/docs/languages
        if lang is not None:
            document["language"] = lang
        response = self.service.classify_text(document)
        self.write_json(json_file, response)
        return response
