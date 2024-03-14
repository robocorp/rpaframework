from typing import Dict, Optional
from google.cloud import vision

from . import keyword


class VisionKeywords:
    """Keywords for Google Vision operations"""

    def __init__(self, ctx):
        self.ctx = ctx
        self.vision_service = None

    @keyword(tags=["init", "vision"])
    def init_vision(
        self,
        service_account: str = None,
        use_robocorp_vault: Optional[bool] = None,
        token_file: str = None,
    ) -> None:
        """Initialize Google Cloud Vision client

        :param service_account: file path to service account file
        :param use_robocorp_vault: use credentials in `Robocorp Vault`
        :param token_file: file path to token file
        """
        self.vision_service = self.ctx.init_service_with_object(
            vision.ImageAnnotatorClient,
            service_account,
            use_robocorp_vault,
            token_file,
        )
        return self.vision_service

    def set_image_type(self, image_file: str = None, image_uri: str = None):
        if image_file:
            with open(image_file, "rb") as f:
                content = f.read()
                return {"image": {"content": content}}
        elif image_uri:
            return {"image": {"source": {"image_uri": image_uri}}}
        else:
            raise KeyError("'image_file' or 'image_uri' is required")

    @keyword(tags=["vision"])
    def detect_labels(
        self, image_file: str = None, image_uri: str = None, json_file: str = None
    ) -> Dict:
        """Detect labels in the image

        :param image_file: source image file path
        :param image_uri: source image uri
        :param json_file: json target to save result
        :return: detection response

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=   Detect Labels   image_file=${CURDIR}${/}test.png
            ...  json_file=${CURDIR}${/}result.json
        """
        parameters = self.set_image_type(image_file, image_uri)
        response = self.vision_service.label_detection(**parameters)
        self.ctx.write_json(json_file, response)
        return response

    @keyword(tags=["vision"])
    def detect_text(
        self, image_file: str = None, image_uri: str = None, json_file: str = None
    ) -> Dict:
        """Detect text in the image

        :param image_file: source image file path
        :param image_uri: Google Cloud Storage URI
        :param json_file: json target to save result
        :return: detection response

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=   Detect Text   image_file=${CURDIR}${/}test.png
            ...  json_file=${CURDIR}${/}result.json
        """
        parameters = self.set_image_type(image_file, image_uri)
        response = self.vision_service.text_detection(**parameters)
        self.ctx.write_json(json_file, response)
        return response

    @keyword(tags=["vision"])
    def detect_document(
        self, image_file: str = None, image_uri: str = None, json_file: str = None
    ) -> Dict:
        """Detect document

        :param image_file: source image file path
        :param image_uri: Google Cloud Storage URI
        :param json_file: json target to save result
        :return: detection response

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=   Detect Document   image_file=${CURDIR}${/}test.png
            ...  json_file=${CURDIR}${/}result.json
        """
        parameters = self.set_image_type(image_file, image_uri)
        response = self.vision_service.document_text_detection(**parameters)
        self.ctx.write_json(json_file, response)
        return response

    @keyword(tags=["vision"])
    def annotate_image(
        self, image_file: str, image_uri: str, json_file: str = None
    ) -> Dict:
        """Annotate image

        :param image_file: source image file path
        :param image_uri: Google Cloud Storage URI
        :param json_file: json target to save result
        :return: detection response

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=   Annotate Image   image_file=${CURDIR}${/}test.png
            ...  json_file=${CURDIR}${/}result.json
        """
        parameters = self.set_image_type(image_file, image_uri)
        response = self.vision_service.annotate_image(**parameters)
        self.ctx.write_json(json_file, response)
        return response

    @keyword(tags=["vision"])
    def face_detection(
        self, image_file: str = None, image_uri: str = None, json_file: str = None
    ) -> Dict:
        """Detect faces

        :param image_file: source image file path
        :param image_uri: Google Cloud Storage URI
        :param json_file: json target to save result
        :return: detection response

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=   Face Detection   image_uri=gs://vision/faces.png
            ...  json_file=${CURDIR}${/}result.json
        """
        parameters = self.set_image_type(image_file, image_uri)
        response = self.vision_service.face_detection(**parameters)
        self.ctx.write_json(json_file, response)
        return response
