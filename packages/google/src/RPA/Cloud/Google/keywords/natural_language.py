from typing import Dict, Optional
from google.cloud import language_v1


from . import LibraryContext, keyword, TextType, to_texttype


class NaturalLanguageKeywords(LibraryContext):
    """Keywords for Google Cloud Natural Language API"""

    def __init__(self, ctx):
        super().__init__(ctx)
        self.service = None

    @keyword(tags=["init", "natural language"])
    def init_natural_language(
        self,
        service_account: str = None,
        use_robocorp_vault: Optional[bool] = None,
        token_file: str = None,
    ) -> None:
        """Initialize Google Cloud Natural Language client

        :param service_account: file path to service account file
        :param use_robocorp_vault: use credentials in `Robocorp Vault`
        :param token_file: file path to token file
        """
        self.service = self.init_service_with_object(
            language_v1.LanguageServiceClient,
            service_account,
            use_robocorp_vault,
            token_file,
        )

    @keyword(tags=["natural language"])
    def analyze_sentiment(
        self,
        text: str = None,
        text_file: str = None,
        file_type: TextType = TextType.TEXT,
        json_file: str = None,
        lang: str = None,
    ) -> Dict:
        """Analyze sentiment in a text file

        :param text: source text
        :param text_file: source text file
        :param file_type: type of text, PLAIN_TEXT (default) or HTML
        :param json_file: json target to save result, defaults to None
        :param lang: language code of the source, defaults to None
        :return: analysis response

        # For list of supported languages:
        # https://cloud.google.com/natural-language/docs/languages

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=   Analyze Sentiment  ${text}
            ${result}=   Analyze Sentiment  text_file=${CURDIR}${/}test.txt
        """
        return self._analyze_handler(
            text, text_file, file_type, json_file, lang, "sentiment"
        )

    @keyword(tags=["natural language"])
    def classify_text(
        self,
        text: str = None,
        text_file: str = None,
        file_type: TextType = TextType.TEXT,
        json_file: str = None,
        lang: str = None,
    ) -> Dict:
        """Classify text

        :param text: source text
        :param text_file: source text file
        :param file_type: type of text, PLAIN_TEXT (default) or HTML
        :param json_file: json target to save result, defaults to None
        :param lang: language code of the source, defaults to None
        :return: classify response

        # For list of supported languages:
        # https://cloud.google.com/natural-language/docs/languages

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=   Classify Text  ${text}
            ${result}=   Classify Text  text_file=${CURDIR}${/}test.txt
        """
        return self._analyze_handler(
            text, text_file, file_type, json_file, lang, "classify"
        )

    def _analyze_handler(
        self, text, text_file, file_type, json_file, lang, analyze_method
    ):
        file_type = to_texttype(file_type)
        parameters = {"type_": file_type}
        if text:
            parameters["content"] = text
        elif text_file:
            with open(text_file, "r") as f:
                parameters["content"] = f.read()
        else:
            raise AttributeError("Either 'text' or 'text_file' must be given")

        if lang is not None:
            parameters["language"] = lang

        document = language_v1.Document(**parameters)
        if analyze_method == "classify":
            response = self.service.classify_text(document=document)
        elif analyze_method == "sentiment":
            # Available values: NONE, UTF8, UTF16, UTF32
            # encoding_type = enums.EncodingType.UTF8
            response = self.service.analyze_sentiment(
                document=document, encoding_type="UTF8"
            )
        self.write_json(json_file, response)
        return response
