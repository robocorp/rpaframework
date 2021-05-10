from typing import Dict, Optional
from google.cloud import speech
from google.cloud.speech_v1.types import RecognitionConfig, RecognitionAudio

from . import (
    LibraryContext,
    keyword,
)

ENCODING = {
    "AMR": RecognitionConfig.AudioEncoding.AMR,
    "AMR_WB": RecognitionConfig.AudioEncoding.AMR_WB,
    "FLAC": RecognitionConfig.AudioEncoding.FLAC,
    "LINEAR16": RecognitionConfig.AudioEncoding.LINEAR16,
    "MULAW": RecognitionConfig.AudioEncoding.MULAW,
    "OGG": RecognitionConfig.AudioEncoding.OGG_OPUS,
    "SPEEX": RecognitionConfig.AudioEncoding.SPEEX_WITH_HEADER_BYTE,  # noqa: E501 # pylint: disable=C0301
    "UNSPECIFIED": RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,  # noqa: E501 # pylint: disable=C0301
}


class SpeechToTextKeywords(LibraryContext):
    """Class for Google Cloud Speech-To-Text API

    Possible input audio encodings:

    - 'AMR'
    - 'AMR_WB'
    - 'ENCODING_UNSPECIFIED'
    - 'FLAC'
    - 'LINEAR16'
    - 'MULAW'
    - 'OGG_OPUS'
    - 'SPEEX_WITH_HEADER_BYTE'

    Link to `Speech To Text PyPI`_ page.

    .. _Speech To Text PyPI: https://pypi.org/project/google-cloud-speech/
    """

    def __init__(self, ctx):
        super().__init__(ctx)
        self.service = None

    @keyword(tags=["init", "speech to text"])
    def init_speech_to_text(
        self,
        service_account: str = None,
        use_robocorp_vault: Optional[bool] = None,
        token_file: str = None,
    ) -> None:
        """Initialize Google Cloud Speech to Text client

        :param service_account: file path to service account file
        :param use_robocorp_vault: use credentials in `Robocorp Vault`
        :param token_file: file path to token file
        """
        self.service = self.init_service_with_object(
            speech.SpeechClient, service_account, use_robocorp_vault, token_file
        )

    @keyword(tags=["speech to text"])
    def recognize_text_from_audio(
        self,
        audio_file: str = None,
        audio_uri: str = None,
        encoding: str = None,
        language_code: str = "en_US",
        audio_channel_count: int = 2,
        sample_rate: int = None,
    ) -> Dict:
        """Recognize text in the audio file

        :param audio_file: local audio file path
        :param audio_uri: Google Cloud Storage URI
        :param encoding: audio file encoding
        :param language_code: language in the audio
        :param audio_channel_count: number of audio channel
        :param sample_rate: rate in hertz, for example 16000
        :return: recognized texts

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=  Recognize Text From Audio   audio_file=${CURDIR}${/}test.mp3
        """
        audio = self.set_audio_type(audio_file, audio_uri)
        parameters = {"use_enhanced": True}
        # audio_encoding = ENCODING["UNSPECIFIED"]
        if encoding and encoding.upper() in ENCODING.keys():
            parameters["encoding"] = ENCODING[encoding.upper()]
        if sample_rate:
            parameters["sample_rate_hertz"] = sample_rate
        if language_code:
            parameters["language_code"] = language_code
        if audio_channel_count:
            parameters["audio_channel_count"] = audio_channel_count
        config = RecognitionConfig(**parameters)  # pylint: disable=E1101
        rec = self.service.recognize(config=config, audio=audio)
        return rec.results

    def set_audio_type(self, audio_file, audio_uri):
        # flac or wav, does not require encoding type
        if audio_file:
            with open(audio_file, "rb") as f:
                content = f.read()
                return RecognitionAudio(content=content)  # pylint: disable=E1101
        elif audio_uri:
            return RecognitionAudio(uri=audio_uri)  # pylint: disable=E1101
        else:
            raise KeyError("'audio_file' or 'audio_uri' is required")
