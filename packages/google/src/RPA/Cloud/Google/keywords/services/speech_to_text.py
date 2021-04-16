from google.cloud import speech


from RPA.Cloud.Google.keywords import (
    LibraryContext,
    keyword,
)

ENCODING = {
    "AMR": speech.enums.RecognitionConfig.AudioEncoding.AMR,
    "AMR_WB": speech.enums.RecognitionConfig.AudioEncoding.AMR_WB,
    "FLAC": speech.enums.RecognitionConfig.AudioEncoding.FLAC,
    "LINEAR16": speech.enums.RecognitionConfig.AudioEncoding.LINEAR16,
    "MULAW": speech.enums.RecognitionConfig.AudioEncoding.MULAW,
    "OGG": speech.enums.RecognitionConfig.AudioEncoding.OGG_OPUS,
    "SPEEX": speech.enums.RecognitionConfig.AudioEncoding.SPEEX_WITH_HEADER_BYTE,  # noqa: E501 # pylint: disable=C0301
    "UNSPECIFIED": speech.enums.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,  # noqa: E501 # pylint: disable=C0301
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
        use_robocloud_vault: bool = False,
    ) -> None:
        """Initialize Google Cloud Speech to Text client

        :param service_account: filepath to credentials JSON
        :param use_robocloud_vault: use json stored into `Robocloud Vault`
        """
        self.init_service_with_object(
            speech.SpeechClient,
            service_account,
            use_robocloud_vault,
        )

    @keyword
    def recognize(
        self,
        audio_file_uri,
        encoding: str = "FLAC",
        language_code: str = "en_US",
        audio_channel_count=2,
    ):
        """Recognize text in the audio file

        :param audio_file_uri: Google Cloud Storage URI
        :return: recognized texts
        """
        # flac or wav, does not require encoding type
        audio = speech.types.RecognitionAudio(  # pylint: disable=E1101
            uri=audio_file_uri
        )
        if encoding and encoding not in ENCODING:
            encoding = ENCODING["UNSPECIFIED"]
        config = speech.types.RecognitionConfig(  # pylint: disable=E1101
            encoding=encoding,
            language_code=language_code,
            audio_channel_count=audio_channel_count,
            use_enhanced=True,
        )
        rec = self.service.recognize(config=config, audio=audio)
        return rec.results
