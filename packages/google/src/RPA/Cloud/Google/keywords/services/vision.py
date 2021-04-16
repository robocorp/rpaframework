from google.cloud import vision


from RPA.Cloud.Google.keywords import (
    LibraryContext,
    keyword,
)


class VisionKeywords(LibraryContext):
    """Keywords for Google Vision operations"""

    def __init__(self, ctx):
        super().__init__(ctx)
        self.service = None

    @keyword
    def init_vision(
        self,
        service_account: str = None,
        use_robocloud_vault: bool = False,
    ) -> None:
        """Initialize Google Cloud Vision client

        :param service_account: filepath to credentials JSON
        :param use_robocloud_vault: use json stored into `Robocloud Vault`
        """
        self.init_service_with_object(
            vision.ImageAnnotatorClient,
            service_account,
            use_robocloud_vault,
        )

    def _get_google_image(self, image_file):
        if not image_file:
            raise KeyError("image_file is required for parameter")
        with open(image_file, "rb") as f:
            content = f.read()
        return vision.types.Image(content=content)  # pylint: disable=E1101

    @keyword
    def detect_labels(self, image_file: str, json_file: str = None) -> dict:
        """Detect labels in the image

        :param image_file: source image file
        :param json_file: json target to save result, defaults to None
        :return: detection response
        """
        image = self._get_google_image(image_file)
        response = self.service.label_detection(image=image)
        self.write_json(json_file, response)
        return response

    @keyword
    def detect_text(self, image_file: str, json_file: str = None) -> dict:
        """Detect text in the image

        :param image_file: source image file
        :param json_file: json target to save result, defaults to None
        :return: detection response
        """
        image = self._get_google_image(image_file)
        response = self.service.text_detection(image=image)
        self.write_json(json_file, response)
        return response

    @keyword
    def detect_document(self, image_file: str, json_file: str = None) -> dict:
        """Detect document

        :param image_file: source image file
        :param json_file: json target to save result, defaults to None
        :return: detection response
        """
        image = self._get_google_image(image_file)
        response = self.service.document_text_detection(image=image)
        self.write_json(json_file, response)
        return response

    @keyword
    def annotate_image(self, image_uri: str, json_file: str = None) -> dict:
        """Annotate image

        :param image_file: source image file
        :param json_file: json target to save result, defaults to None
        :return: detection response
        """
        response = self.service.annotate_image(
            {"image": {"source": {"image_uri": image_uri}}}
        )
        self.write_json(json_file, response)
        return response

    @keyword
    def face_detection(self, image_uri: str, json_file: str = None) -> dict:
        """Detect faces

        :param image_uri: Google Cloud Storage URI
        :param json_file: json target to save result, defaults to None
        :return: detection response
        """
        response = self.service.face_detection({"source": {"image_uri": image_uri}})
        self.write_json(json_file, response)
        return response
