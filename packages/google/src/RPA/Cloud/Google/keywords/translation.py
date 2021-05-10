from typing import Dict, Union, Optional

from google.cloud import translate_v3

from . import LibraryContext, keyword, TextType, to_texttype


class TranslationKeywords(LibraryContext):
    """Class for Google Cloud Translation API

    Link to `Translation PyPI`_ page.

    .. _Translation PyPI: https://pypi.org/project/google-cloud-translate/
    """

    def __init__(self, ctx):
        super().__init__(ctx)
        self.service = None
        self.project_id = None

    @keyword(tags=["init", "translation"])
    def init_translation(
        self,
        project_identifier: str,
        service_account: str = None,
        use_robocorp_vault: Optional[bool] = None,
        token_file: str = None,
    ) -> None:
        """Initialize Google Cloud Translation client

        :param project_identifier: identifier for Translation project
        :param service_account: file path to service account file
        :param use_robocorp_vault: use credentials in `Robocorp Vault`
        :param token_file: file path to token file
        """
        self.project_id = project_identifier
        self.service = self.init_service_with_object(
            translate_v3.TranslationServiceClient,
            service_account,
            use_robocorp_vault,
            token_file,
        )

    @keyword(tags=["translation"])
    def translate(
        self,
        text: Union[list, str],
        source_language: str = None,
        target_language: str = None,
        mime_type: TextType = None,
    ) -> Dict:
        """Translate text

        :param text: text to translate
        :param source_language: language code
        :param target_language: language code
        :param mime_type: text or html
        :return: translated text

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=   Translate   ${TEXT}  target_language=de
        """
        if not text and not target_language:
            raise KeyError("text and target_language are required parameters")
        parent = f"projects/{self.project_id}"
        contents = [text] if not isinstance(text, list) else text

        parameters = {"parent": parent, "contents": contents}
        if source_language:
            parameters["source_language_code"] = source_language
        if target_language:
            parameters["target_language_code"] = target_language
        if mime_type:
            mimetype = to_texttype(mime_type)
            parameters["mime_type"] = mimetype
        response = self.service.translate_text(**parameters)
        return response
