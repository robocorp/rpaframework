import base64
import itertools
import logging
import mimetypes
import urllib.parse as urlparse
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
import validators

from RPA.JSON import JSONType
from RPA.Robocorp.utils import PathType, get_output_dir
from RPA.RobotLogListener import RobotLogListener


class Base64AI:
    """Library to support `Base64.ai <https://base64.ai/>`_ service for intelligent
    document processing (IDP).

    Library requires at the minimum `rpaframework` version **19.0.0**.

    Service supports identifying fields in the documents, which can be given to the
    service in multiple different file formats and via URL.

    **Robot Framework example usage**

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.DocumentAI.Base64AI
        Library   RPA.Robocorp.Vault

        *** Tasks ***
        Identify document
            ${secrets}=   Get Secret  base64ai-auth
            Set Authorization  ${secrets}[email-address]   ${secrets}[apikey]
            ${results}=  Scan Document File
            ...   ${CURDIR}${/}invoice.pdf
            ...   model_types=finance/check/usa,finance/invoice/usa
            # Scan response contains list of detected models in the document
            FOR  ${result}  IN  @{results}
                Log To Console  Model: ${result}[model]
                Log To Console  Field keys: ${{','.join($result['fields'].keys())}}
                Log To Console  Fields: ${result}[fields]
                Log To Console  Text (OCR): ${result}[ocr]
            END


    **Python example usage**

    .. code-block:: python

        from RPA.DocumentAI.Base64AI import Base64AI
        from RPA.Robocorp.Vault import Vault

        secrets = Vault().get_secret("base64ai-auth")
        baselib = Base64AI()
        baselib.set_authorization(secrets["email-address"], secrets["apikey"])
        result = baselib.scan_document_file(
            "invoice.pdf",
            model_types="finance/invoice,finance/check/usa",
        )
        for r in result:
            print(f"Model: {r['model']}")
            for key, props in r["fields"].items():
                print(f"FIELD {key}: {props['value']}")
            print(f"Text (OCR): {r['ocr']}")

    Portal example: https://github.com/robocorp/example-idp-base64
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    BASE_URL = "https://base64.ai"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._request_headers = {"Content-Type": "application/json"}
        listener = RobotLogListener()
        listener.register_protected_keywords(
            ["RPA.DocumentAI.Base64AI.set_authorization"]
        )

    def set_authorization(self, api_email: str, api_key: str) -> None:
        """Set Base64 AI request headers with email and key related to API.

        :param api_email: email address related to the API
        :param api_key: key related to the API

        Robot Framework example:

        .. code-block:: robotframework

            ${secrets}=   Get Secret  base64ai-auth
            Set Authorization    ${secrets}[email-address]    ${secrets}[apikey]

        Python example:

        .. code-block:: python

            secrets = Vault().get_secret("base64ai-auth")
            baselib = Base64AI()
            baselib.set_authorization(secrets["email-address"], secrets["apikey"])
        """
        self._request_headers["Authorization"] = f"ApiKey {api_email}:{api_key}"

    @classmethod
    def _to_endpoint(cls, part: str, mock: bool = False) -> str:
        return urlparse.urljoin(
            cls.BASE_URL, f"{'mock' if mock else 'api'}/{part.strip('/')}"
        )

    def _scan_document(
        self,
        payload: Dict,
        model_types: Optional[Union[str, List[str]]] = None,
        mock: bool = False,
    ) -> JSONType:
        scan_endpoint = self._to_endpoint("scan", mock=mock)
        self.logger.info(f"Endpoint {scan_endpoint!r} is set for scanning.")
        if model_types:
            req_model_types = (
                model_types if isinstance(model_types, list) else model_types.split(",")
            )
            payload["modelTypes"] = req_model_types

        response = requests.post(
            scan_endpoint,
            headers=self._request_headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _get_file_base64_and_mimetype(file_path: str) -> Tuple[str, str]:
        with open(file_path, "rb") as image_file:
            encoded_content = base64.b64encode(image_file.read())
        return encoded_content.decode("utf-8"), mimetypes.guess_type(file_path)[0]

    @classmethod
    def _url_or_file(cls, resource: str, data_only: bool = False) -> Tuple[str, bool]:
        # Returns the URL string (or file API-ready content) and resource type.
        #  (`True` if URL)
        if not data_only and validators.url(resource):
            return resource, True

        # We're dealing with a file then.
        base64string, mime = cls._get_file_base64_and_mimetype(resource)
        data = f"data:{mime};base64,{base64string}"
        return data, False

    def scan_document_file(
        self,
        file_path: str,
        model_types: Optional[Union[str, List[str]]] = None,
        mock: bool = False,
    ) -> JSONType:
        """Scan a document file. Can be given a ``model_types`` to
        specifically target certain models.

        :param file_path: filepath to the file
        :param model_types: single model type or list of model types
        :param mock: set to True to use /mock/scan endpoint instead of /scan
        :return: result of the document scan

        Robot Framework example:

        .. code-block:: robotframework

            ${results}=    Scan Document File
            ...    ${CURDIR}${/}files${/}IMG_8277.jpeg
            ...    model_types=finance/check/usa,finance/invoice
            FOR    ${result}    IN    @{results}
                Log To Console    Model: ${result}[model]
                Log To Console    Fields: ${result}[fields]
                Log To Console    Text (OCR): ${result}[ocr]
            END

        Python example:

        .. code-block:: python

            result = baselib.scan_document_file(
                "./files/Invoice-1120.pdf",
                model_types="finance/invoice,finance/check/usa",
            )
            for r in result:
                print(f"Model: {r['model']}")
                for key, val in r["fields"].items():
                    print(f"{key}: {val['value']}")
                print(f"Text (OCR): {r['ocr']}")
        """
        data, _ = self._url_or_file(file_path, data_only=True)
        payload = {"image": data}
        return self._scan_document(payload, model_types=model_types, mock=mock)

    def scan_document_url(
        self,
        url: str,
        model_types: Optional[Union[str, List[str]]] = None,
        mock: bool = False,
    ) -> JSONType:
        """Scan a document URL. Can be given a ``model_types`` to
        specifically target certain models.

        :param url: valid url to a file
        :param model_types: single model type or list of model types
        :param mock: set to True to use /mock/scan endpoint instead of /scan
        :return: result of the document scan

        Robot Framework example:

        .. code-block:: robotframework

            ${results}=    Scan Document URL
            ...    https://base64.ai/static/content/features/data-extraction/models//2.png
            FOR    ${result}    IN    @{results}
                Log To Console    Model: ${result}[model]
                Log To Console    Fields: ${result}[fields]
                Log To Console    Text (OCR): ${result}[ocr]
            END

        Python example:

        .. code-block:: python

            result = baselib.scan_document_url(
                "https://base64.ai/static/content/features/data-extraction/models//2.png"
            )
            for r in result:
                print(f"Model: {r['model']}")
                for key, props in r["fields"].items():
                    print(f"FIELD {key}: {props['value']}")
                print(f"Text (OCR): {r['ocr']}")
        """  # noqa: E501
        payload = {"url": url}
        return self._scan_document(payload, model_types=model_types, mock=mock)

    def get_fields_from_prediction_result(self, prediction: JSONType) -> List:
        """Helper keyword to get found fields from a prediction result.
        For example see ``Scan Document File`` or ``Scan Document URL`` keyword.

        :param prediction: prediction result dictionary
        :return: list of found fields
        """
        return list(
            itertools.chain(*(list(item["fields"].values()) for item in prediction))
        )

    def get_user_data(self) -> Dict:
        """Get user data including details on credits used and credits remaining
        for the Base64 service.

        Returned user data contains following keys:

            - givenName
            - familyName
            - email
            - hasWorkEmail
            - companyName
            - numberOfCredits
            - numberOfPages
            - numberOfUploads
            - numberOfCreditsSpentOnDocuments (visible if used)
            - numberOfCreditsSpentOnFaceDetection (visible if used)
            - numberOfCreditsSpentOnFaceRecognition (visible if used)
            - hasActiveAwsContract
            - subscriptionType
            - subscriptionPeriod
            - tags
            - ccEmails
            - status
            - remainingCredits (calculated by the keyword)

        :return: object containing details on the API user

        Robot Framework example:

        .. code-block:: robotframework

            ${userdata}=   Get User Data
            Log To Console  I have still ${userdata}[remainingCredits] credits left

        Python example:

        .. code-block:: python

            userdata = baselib.get_user_data()
            print(f"I have still {userdata['remainingCredits']} credits left")
        """
        response = requests.get(
            self._to_endpoint("auth/user"),
            headers=self._request_headers,
        )
        response.raise_for_status()
        json_response = response.json()
        spent_on_documents = json_response.get("numberOfCreditsSpentOnDocuments", 0)
        spent_on_face_detection = json_response.get(
            "numberOfCreditsSpentOnFaceDetection", 0
        )
        spent_on_face_recognition = json_response.get(
            "numberOfCreditsSpentOnFaceRecognition", 0
        )
        remainingCredits = (
            json_response["numberOfCredits"]
            - spent_on_documents
            - spent_on_face_detection
            - spent_on_face_recognition
        )
        json_response["remainingCredits"] = remainingCredits
        return json_response

    def get_matching_signatures(
        self, reference_image: PathType, query_image: PathType
    ) -> JSONType:
        """Returns a list of matching signatures found from the reference into the
        queried image.

        The output JSON-like dictionary contains all the details from the API, like the
        detected signatures in both the reference and query image and for every such
        signature, its bounding-box geometry, confidence and similarity score.
        Use the ``Filter Matching Signatures`` over this value to get a simpler
        structure.

        :param reference_image: The reference image (jpg/png) to check query signatures
            against. (e.g. driving license, ID card)
        :param query_image: The query image containing signatures similar to the ones
            from the reference image. (e.g. signed contract, bank check)
        :returns: A JSON-like dictionary revealing recognized signatures and how much
            they resemble with each other.

        **Example: Robot Framework**

        .. code-block:: robotframework

            *** Tasks ***
            Match Signatures
                ${ref_image} =  Set Variable    driving-license.jpg
                ${query_image} =  Set Variable    signed-check.png
                ${sigs} =   Get Matching Signatures     ${ref_image}    ${query_image}

        **Example: Python**

        .. code-block:: python

            from RPA.DocumentAI.Base64AI import Base64AI

            lib = Base64AI()
            sigs = lib.get_matching_signatures(
                "driving-license.jpg", "signed-check.png"
            )

        Portal example: https://github.com/robocorp/example-signature-match-assistant
        """
        # NOTE(cmin764): There's no mock support for this API.
        recognize_endpoint = self._to_endpoint("signature/recognize")

        payload = {
            "reference": str(reference_image),
            "query": str(query_image),
        }
        for key, value in list(payload.items()):
            value, is_url = self._url_or_file(value)
            key += "Url" if is_url else "Image"
            payload[key] = value
        del payload["reference"]
        del payload["query"]

        response = requests.post(
            recognize_endpoint,
            headers=self._request_headers,
            json=payload,
        )
        response.raise_for_status()
        match_response = response.json()
        return match_response

    def filter_matching_signatures(
        self,
        match_response: JSONType,
        confidence_threshold: float = 0.8,
        similarity_threshold: float = 0.8,
    ) -> Dict[Tuple[int, Tuple[int, ...]], List[Dict[str, Any]]]:
        """Gets through all the recognized signatures in the queried image and returns
        only the ones passing the confidence & similarity thresholds.

        Additionally, this keyword simplifies the original input `match_response`
        structure and returns a dictionary with all the detected and accepted reference
        signatures as keys, and lists of similar enough query signatures as values.

        - Each reference signature (key) is a tuple of `(index, coordinates)`.
        - Each query signature (sub-value) is a dictionary of `{index, coords,
          similarity}`.
        - The coordinates describe the bounding-box enclosing the detected signature
          portion from the original image, as follows: `(left, top, right, bottom)`
          corners.

        Use the original `match_response` object and the indexes from here if you need
        to retrieve extra details not found here (e.g. confidence score). Use the
        ``Get Signature Image`` to save and preview the image crop belonging to the
        signature of choice.

        :param match_response: The raw JSON-like response retrieved with the
            ``Get Matching Signatures`` keyword.
        :param confidence_threshold: The minimum accepted confidence score (0.0-1.0)
            for a candidate to be considered a signature. (to avoid false-positives)
        :param similarity_threshold: The minimum accepted similarity score (0.0-1.0)
            for a query signature to be considered an alike signature. (to discard
            different or fraudulent signatures)
        :returns: A dictionary of accepted reference signatures and their similar ones
            found in the queried image.

        **Example: Robot Framework**

        .. code-block:: robotframework

            *** Tasks ***
            Match Signatures
                &{matches} =   Filter Matching Signatures      ${sigs}
                Log Dictionary    ${matches}

        **Example: Python**

        .. code-block:: python

            matches = lib.filter_matching_signatures(sigs)
            print(matches)
        """
        accepted_references = [
            ref["confidence"] >= confidence_threshold
            for ref in match_response["reference"]
        ]
        candidates = {}
        # As (left, top, right, bottom) tuple.
        to_coords = lambda item: (  # noqa: E731
            item["left"],
            item["top"],
            item["left"] + item["width"],  # right corner
            item["top"] + item["height"],  # bottom corner
        )

        for qry_idx, candidate in enumerate(match_response["query"]):
            if candidate["confidence"] < confidence_threshold:
                continue  # not sure enough it is a signature

            qry_coords = to_coords(candidate)
            for ref_idx, similarity in enumerate(candidate["similarities"]):
                if (
                    not accepted_references[ref_idx]
                    or similarity < similarity_threshold
                ):
                    # Skip any resemblance to doubtful reference signatures.
                    # Skip not similar enough signatures.
                    continue

                # Filtered properties for the accepted match.
                qry_body = {
                    "index": qry_idx,
                    "coords": qry_coords,
                    "similarity": similarity,
                }
                # Every accepted reference signature (index, coordinates) contains a
                #  list of similar recognized signatures from the queried image, as
                #  {index, coordinates, similarity}.
                ref_coords = to_coords(match_response["reference"][ref_idx])
                # Example of such candidate dictionary entry:
                #  (0, (92, 509, 234, 616)): [{'index': 0, 'coords': (1812, 813, 2114, 1035), 'similarity': 0.89}]  # noqa: E501
                candidates.setdefault((ref_idx, ref_coords), []).append(qry_body)

        for matches in candidates.values():
            matches.sort(key=lambda body: body["similarity"], reverse=True)
        return candidates

    def get_signature_image(
        self,
        match_response: JSONType,
        *,
        index: int,
        reference: bool = False,
        path: Optional[PathType] = None,
    ) -> str:
        """Retrieves and saves locally the image cut belonging to the provided `index`.

        The image data itself is provided with the original `match_response` object as
        base64 encoded content. This utility keyword retrieves, decodes and saves it
        on the local disk customized with the `path` parameter. By default, the
        searched `index` is considered a query image, switch to the reference type by
        enabling it with the `reference` parameter.

        :param match_response: The raw JSON-like response retrieved with the
            ``Get Matching Signatures`` keyword.
        :param index: The image ID (numeric) found along the coordinates in the output
            of the ``Filter Matching Signatures`` keyword. (the list order is stable)
        :param reference: Set this to `True` if you're looking for a reference (not
            query) image instead. (off by default)
        :param path: Set an explicit output path (including file name) for the locally
            saved image. (uses the output directory as default)
        :returns: The image path of the locally saved file.

        **Example: Robot Framework**

        .. code-block:: robotframework

            *** Tasks ***
            Match Signatures
                @{ref_sigs} =   Get Dictionary Keys    ${matches}
                @{qry_sigs} =    Get From Dictionary    ${matches}    ${ref_sigs}[${0}]
                &{qry_sig} =    Set Variable    ${qry_sigs}[${0}]
                ${path} =   Get Signature Image     ${sigs}     index=${qry_sig}[index]
                Log To Console    Preview query signature image crop: ${path}

        **Example: Python**

        .. code-block:: python

            qry_sig = list(matches.values())[0][0]
            path = lib.get_signature_image(sigs, index=qry_sig["index"])
            print("Preview query signature image crop: ", path)
        """
        images_type = "reference" if reference else "query"
        images = match_response[images_type]
        encoded_content = images[index]["image"]
        image_format, image_content = encoded_content.split(";base64,")
        decoded_bytes = base64.b64decode(image_content.encode())
        image_ext = image_format.split("/")[-1]
        path = path or (get_output_dir() / f"{images_type}-{index}.{image_ext}")
        with open(path, "wb") as stream:
            stream.write(decoded_bytes)
        return str(path)
