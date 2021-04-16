from enum import Enum
from typing import List

from google.cloud import videointelligence

from RPA.Cloud.Google.keywords import (
    LibraryContext,
    keyword,
)


class VideoFeature(Enum):
    """Possible video features."""

    FEATURE_UNSPECIFIED = "FEATURE_UNSPECIFIED"
    LABEL_DETECTION = "LABEL_DETECTION"
    SHOT_CHANGE_DETECTION = "SHOT_CHANGE_DETECTION"
    EXPLICIT_CONTENT_DETECTION = "EXPLICIT_CONTENT_DETECTION"
    SPEECH_TRANSCRIPTION = "SPEECH_TRANSCRIPTION"
    TEXT_DETECTION = "TEXT_DETECTION"
    OBJECT_TRACKING = "OBJECT_TRACKING"
    LOGO_RECOGNITION = "LOGO_RECOGNITION"


class VideoIntelligenceKeywords(LibraryContext):
    """Keywords for Google Video Intelligence API"""

    def __init__(self, ctx):
        super().__init__(ctx)
        self.service = None

    @keyword
    def init_video_intelligence(
        self,
        service_account: str = None,
        use_robocloud_vault: bool = False,
    ) -> None:
        """Initialize Google Cloud Video Intelligence client

        :param service_account: filepath to credentials JSON
        :param use_robocloud_vault: use json stored into `Robocloud Vault`
        """
        self.init_service_with_object(
            videointelligence.VideoIntelligenceServiceClient,
            service_account,
            use_robocloud_vault,
        )

    @keyword
    def annotate_video(
        self,
        video_uri: str = None,
        video_file: str = None,
        json_file: str = None,
        features: List[VideoFeature] = None,
    ):
        """Annotate video

        Possible values for features:

        - FEATURE_UNSPECIFIED, Unspecified.
        - LABEL_DETECTION, Label detection. Detect objects, such as dog or flower.
        - SHOT_CHANGE_DETECTION, Shot change detection.
        - EXPLICIT_CONTENT_DETECTION, Explicit content detection.
        - SPEECH_TRANSCRIPTION, Speech transcription.
        - TEXT_DETECTION, OCR text detection and tracking.
        - OBJECT_TRACKING, Object detection and tracking.
        - LOGO_RECOGNITION, Logo detection, tracking, and recognition.

        If `video_uri` is given then that is used even if `video_file` is None.

        :param video_uri: Google Cloud Storage URI
        :param video_file: filepath to video
        :param json_file: json target to save result, defaults to None
        :param features: list of annotation features to detect,
            defaults to ["LABEL_DETECTION", "SHOT_CHANGE_DETECTION"]
        :return: annotate result
        """
        response = None
        if features is None:
            features = [
                VideoFeature.LABEL_DETECTION,
                VideoFeature.SHOT_CHANGE_DETECTION,
            ]
        if video_uri:
            response = self.service.annotate_video(
                input_uri=video_uri, features=features
            ).result()
        elif video_file:
            with open(video_file, "rb") as f:
                response = self.service.annotate_video(
                    input_content=f.read(), features=features
                ).result()
        self.write_json(json_file, response)
        return response
