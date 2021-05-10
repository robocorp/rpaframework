from typing import Dict, Optional

from google.cloud import videointelligence

from . import LibraryContext, keyword, to_feature


class VideoIntelligenceKeywords(LibraryContext):
    """Keywords for Google Video Intelligence API"""

    def __init__(self, ctx):
        super().__init__(ctx)
        self.service = None

    @keyword(tags=["init", "video intelligence"])
    def init_video_intelligence(
        self,
        service_account: str = None,
        use_robocorp_vault: Optional[bool] = None,
        token_file: str = None,
    ) -> None:
        """Initialize Google Cloud Video Intelligence client

        :param service_account: file path to service account file
        :param use_robocorp_vault: use credentials in `Robocorp Vault`
        :param token_file: file path to token file
        """
        self.service = self.init_service_with_object(
            videointelligence.VideoIntelligenceServiceClient,
            service_account,
            use_robocorp_vault,
            token_file,
        )

    @keyword(tags=["video intelligence"])
    def annotate_video(
        self,
        video_file: str = None,
        video_uri: str = None,
        features: str = None,
        output_uri: str = None,
        json_file: str = None,
        timeout: int = 300,
    ) -> Dict:
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

        If `video_uri` is given then that is used even if `video_file` is given.

        :param video_file: local file path to input video
        :param video_uri: Google Cloud Storage URI to input video
        :param features: list of annotation features to detect,
            defaults to LABEL_DETECTION,SHOT_CHANGE_DETECTION
        :param output_uri: Google Cloud Storage URI to store response json
        :param json_file: json target to save result
        :param timeout: timeout for operation in seconds
        :return: annotate result

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=   Annotate Video   video_uri=gs://videointelligence/movie.mp4
            ...  features=TEXT_DETECTION,LABEL_DETECTION
            ...  output_uri=gs://videointelligence/movie_annotations.json
            ...  json_file=${CURDIR}${/}videoannotations.json
        """
        if features is None:
            features_in = [
                videointelligence.Feature.LABEL_DETECTION,
                videointelligence.Feature.SHOT_CHANGE_DETECTION,
            ]
        else:
            features_in = [to_feature(feature) for feature in features.split(",")]
        parameters = {"features": features_in}
        if video_uri:
            parameters["input_uri"] = video_uri
        elif video_file:
            video_context = videointelligence.VideoContext()
            with open(video_file, "rb") as file:
                input_content = file.read()
                parameters["input_content"] = input_content
                parameters["video_context"] = video_context
        if output_uri:
            parameters["output_uri"] = output_uri

        operation = self.service.annotate_video(request=parameters)
        result = operation.result(timeout=timeout)
        self.write_json(json_file, result)
        return result
