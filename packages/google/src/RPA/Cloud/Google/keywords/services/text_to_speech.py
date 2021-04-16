from google.cloud import texttospeech_v1
from google.cloud.texttospeech_v1.types import (
    AudioConfig,
    VoiceSelectionParams,
    SynthesisInput,
)

from RPA.Cloud.Google.keywords import (
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

    @keyword
    def init_text_to_speech(
        self, service_account: str = None, use_robocloud_vault: bool = False
    ) -> None:
        """Initialize Google Cloud Text to Speech client

        :param service_credentials_file: filepath to credentials JSON
        :param use_robocloud_vault: use json stored into `Robocloud Vault`
        """
        self.init_service_with_object(
            texttospeech_v1.TextToSpeechClient,
            service_account,
            use_robocloud_vault,
        )

    @keyword
    def list_supported_voices(self, language_code: str = None):
        """List supported voices for the speech

        :param language_code: voice languages to list, defaults to None (all)
        :return: list of supported voices
        """
        if language_code:
            voices = self.service.list_voices(language_code)
        else:
            voices = self.service.list_voices()
        return voices.voices

    @keyword
    def synthesize_speech(
        self,
        text,
        language="en-US",
        name="en-US-Standard-B",
        gender="MALE",
        encoding="MP3",
        target_file="synthesized.mp3",
    ):
        """Synthesize speech synchronously

        :param text: input text to synthesize
        :param language: voice language, defaults to "en-US"
        :param name: voice name, defaults to "en-US-Standard-B"
        :param gender: voice gender, defaults to "MALE"
        :param encoding: result encoding type, defaults to "MP3"
        :param target_file: save synthesized output to file,
            defaults to "synthesized.mp3"
        :return: synthesized output in bytes
        """
        if not text:
            raise KeyError("text is required for kw: synthesize_speech")
        synth_input = SynthesisInput(text=text)
        voice_selection = VoiceSelectionParams(
            language_code=language, name=name, ssml_gender=gender
        )
        audio_config = AudioConfig(audio_encoding=encoding)
        response = self.service.synthesize_speech(
            synth_input, voice_selection, audio_config
        )
        if target_file:
            with open(target_file, "wb") as f:
                f.write(response.audio_content)
        return response.audio_content
