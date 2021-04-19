from typing import Optional
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

    @keyword
    def init_speech_to_text(
        self,
        service_account: str = None,
        use_robocloud_vault: Optional[bool] = None,
    ) -> None:
        """Initialize Google Cloud Speech to Text client

        :param service_account: filepath to credentials JSON
        :param use_robocloud_vault: use json stored into `Robocloud Vault`
        """
        self.service = self.init_service_with_object(
            speech.SpeechClient,
            service_account,
            use_robocloud_vault,
        )

    @keyword
    def recognize(
        self,
        audio_file: str = None,
        audio_uri: str = None,
        encoding: str = None,
        language_code: str = "en_US",
        audio_channel_count=2,
    ):
        """Recognize text in the audio file

        :param audio_file_uri: Google Cloud Storage URI
        :return: recognized texts

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=  Recognize   audio_file=${CURDIR}${/}test.mp3
        """

        audio = self.set_audio_type(audio_file, audio_uri)
        audio_encoding = ENCODING["UNSPECIFIED"]
        if encoding and encoding.upper() in ENCODING.keys():
            audio_encoding = ENCODING[encoding.upper()]
        config = RecognitionConfig(  # pylint: disable=E1101
            encoding=audio_encoding,
            language_code=language_code,
            sample_rate_hertz=16000,
            audio_channel_count=audio_channel_count,
            use_enhanced=True,
        )
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
