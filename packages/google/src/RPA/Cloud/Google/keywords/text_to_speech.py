from typing import List, Optional

from google.cloud import texttospeech_v1
from google.cloud.texttospeech_v1.types import (
    AudioConfig,
    VoiceSelectionParams,
    SynthesisInput,
)

from . import (
    LibraryContext,
    keyword,
)


class TextToSpeechKeywords(LibraryContext):
    """Class for Google Cloud Text-to-Speech API

    Link to `Text To Speech PyPI`_ page.

    .. _Text To Speech PyPI: https://pypi.org/project/google-cloud-texttospeech/
    """

    def __init__(self, ctx):
        super().__init__(ctx)
        self.service = None

    @keyword(tags=["init", "text to speech"])
    def init_text_to_speech(
        self,
        service_account: str = None,
        use_robocorp_vault: Optional[bool] = None,
        token_file: str = None,
    ) -> None:
        """Initialize Google Cloud Text to Speech client

        :param service_account: file path to service account file
        :param use_robocorp_vault: use credentials in `Robocorp Vault`
        :param token_file: file path to token file
        """
        self.service = self.init_service_with_object(
            texttospeech_v1.TextToSpeechClient,
            service_account,
            use_robocorp_vault,
            token_file,
        )

    @keyword(tags=["text to speech"])
    def list_supported_voices(self, language_code: str = None) -> List:
        """List supported voices for the speech

        :param language_code: voice languages to list, defaults to None (all)
        :return: list of supported voices

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=   List Supported Voices   en-US
        """
        if language_code:
            voices = self.service.list_voices(language_code)
        else:
            voices = self.service.list_voices()
        return voices.voices

    @keyword(tags=["text to speech"])
    def synthesize_speech(
        self,
        text: str,
        language: str = "en-US",
        name: str = "en-US-Standard-B",
        gender: str = "MALE",
        encoding: str = "MP3",
        target_file: str = "synthesized.mp3",
    ) -> List:
        """Synthesize speech synchronously

        :param text: input text to synthesize
        :param language: voice language, defaults to "en-US"
        :param name: voice name, defaults to "en-US-Standard-B"
        :param gender: voice gender, defaults to "MALE"
        :param encoding: result encoding type, defaults to "MP3"
        :param target_file: save synthesized output to file,
            defaults to "synthesized.mp3"
        :return: synthesized output in bytes

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=   Synthesize Speech   ${text}
        """
        synth_input = SynthesisInput(text=text)
        voice_selection = VoiceSelectionParams(
            language_code=language, name=name, ssml_gender=gender
        )
        audio_config = AudioConfig(audio_encoding=encoding)
        response = self.service.synthesize_speech(
            request={
                "input": synth_input,
                "voice": voice_selection,
                "audio_config": audio_config,
            }
        )
        if target_file:
            with open(target_file, "wb") as f:
                f.write(response.audio_content)
        return response.audio_content
