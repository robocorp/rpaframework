from typing import Any

from google.cloud import translate_v3

from RPA.Cloud.Google.keywords import (
    LibraryContext,
    keyword,
)


class TranslationKeywords(LibraryContext):
    """Class for Google Cloud Translation API

    Link to `Translation PyPI`_ page.

    .. _Translation PyPI: https://pypi.org/project/google-cloud-translate/
    """

    def __init__(self, ctx):
        super().__init__(ctx)
        self.service = None
        self.project_id = None

    @keyword
    def init_translation(
        self,
        service_account: str = None,
        project_identifier: str = None,
        use_robocloud_vault: bool = False,
    ) -> None:
        """Initialize Google Cloud Translation client

        :param service_account: filepath to credentials JSON
        :param project_identifier: identifier for Translation project
        :param use_robocloud_vault: use json stored into `Robocloud Vault`
        """
        self.init_service_with_object(
            translate_v3.TranslationServiceClient,
            service_account,
            use_robocloud_vault,
        )
        self.project_id = project_identifier

    @keyword
    def translate(
        self, text: Any, source_language: str = None, target_language: str = None
    ) -> dict:
        """Translate text

        :param text: text to translate
        :param source_language: language code, defaults to None
        :param target_language: language code, defaults to None
        :return: translated text
        """
        if not text and not target_language:
            raise KeyError("text and target_language are required parameters")
        parent = self.service.location_path(self.project_id, "global")
        if isinstance(text, str):
            text = [text]
        response = self.service.translate_text(
            contents=text,
            source_language_code=source_language,
            target_language_code=target_language,
            parent=parent,
        )
        return response
