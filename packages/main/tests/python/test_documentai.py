"""Testing of RPA.DocumentAI library."""


import json
from pathlib import Path

import pytest
from unittest import mock

from RPA.DocumentAI import DocumentAI
from RPA.DocumentAI.Base64AI import Base64AI
from RPA.DocumentAI.DocumentAI import EngineName
from RPA.DocumentAI.Nanonets import Nanonets

from . import RESOURCES_DIR, RESULTS_DIR


DOCAI_DIR = RESOURCES_DIR / "documentai"


class TestDocumentAI:
    """Tests `RPA.DocumentAI`."""

    @staticmethod
    @pytest.fixture
    def library():
        return DocumentAI()

    @staticmethod
    @pytest.fixture
    def invoice_png():
        return RESOURCES_DIR / "invoice.png"

    @pytest.mark.xfail(reason="`rpaframework-google` is unexpectedly available in venv")
    def test_init_engine_google(self, library):
        # As `rpaframework-google` isn't installed by default.
        with pytest.raises(ImportError):
            library.init_engine("google")

    def test_init_engine_base64(self, library):
        secret = "cosmin@robocorp.com,api-key"
        with pytest.raises(TypeError):
            # Two arguments (positional or keyword) are required.
            library.init_engine("base64ai", secret="api-key")
        library.init_engine("base64ai", secret=secret)
        engine = library.engine
        assert isinstance(engine, Base64AI)
        assert secret.replace(",", ":") in engine._request_headers["Authorization"]

    def test_init_engine_nanonets(self, library):
        secret = "api-key"
        library.init_engine("nanonets", secret=secret)
        engine = library.engine
        assert isinstance(engine, Nanonets)
        assert secret == library.engine.apikey

    def test_switch_engine(self, library):
        with pytest.raises(RuntimeError):
            assert library.engine  # no engine initialized

        library.init_engine("base64ai", secret="cosmin@robocorp.com,api-key")
        library.init_engine("nanonets", secret="api-key")

        assert isinstance(library.engine, Nanonets)
        library.switch_engine(EngineName.BASE64)
        assert isinstance(library.engine, Base64AI)

    @mock.patch("RPA.DocumentAI.Base64AI.requests")
    def test_predict_base64(self, mock_requests, library, invoice_png):
        library.init_engine("base64ai", secret="cosmin@robocorp.com,api-key")
        model = "invoice-model"
        library.predict(invoice_png, model=model)
        args, kwargs = mock_requests.post.call_args
        assert args == ("https://base64.ai/api/scan",)
        assert model in kwargs["json"]["modelTypes"]

    @mock.patch("RPA.DocumentAI.Nanonets.requests")
    def test_predict_nanonets(self, mock_requests, library, invoice_png):
        library.init_engine("nanonets", secret="api-key")
        model = "invoice-model"
        library.predict(invoice_png, model=model)
        args, kwargs = mock_requests.post.call_args
        assert args == (
            "https://app.nanonets.com/api/v2/OCR/Model/invoice-model/LabelFile/",
        )
        assert kwargs["files"]["file"].name == str(invoice_png)

    @pytest.mark.parametrize("extended", [False, True])
    def test_get_result(self, library, extended):
        library.init_engine("nanonets", secret="api-key")
        prediction = {
            "result": [
                {
                    "prediction": [
                        {
                            "id": "251fed51-e1fa-477e-af9d-3fe115486290",
                            "label": "bank_name",
                            "xmin": 901,
                            "ymin": 1619,
                            "xmax": 1001,
                            "ymax": 1629,
                            "score": 0.5428322,
                            "ocr_text": "Deutsche Bank",
                            "type": "field",
                            "status": "correctly_predicted",
                            "page_no": 0,
                            "label_id": "d5513122-0a46-4927-b923-cd9e6eed758d",
                        },
                        {"extra": "field"},
                    ]
                }
            ]
        }
        library._results[library._active_engine] = prediction
        result = library.get_result(extended=extended)
        if extended:
            assert result == prediction
        else:
            assert result[0]["ocr_text"] == "Deutsche Bank"


class TestBase64AI:
    """Tests `RPA.DocumentAI.Base64AI`."""

    @staticmethod
    @pytest.fixture
    def library():
        return Base64AI()

    @staticmethod
    @pytest.fixture
    def input_files():
        paths = {
            "driving-license": DOCAI_DIR / "signature-license.jpg",
            "payment-check": DOCAI_DIR / "signature-check.png",
        }
        urls = {
            "driving-license": (
                "https://raw.githubusercontent.com/robocorp/rpaframework/5d8f3db0e3fe5"
                "5396afccd987afaa1f389df2527/packages/main/tests/resources/documentai/"
                "signature-license.jpg"
            ),
            "payment-check": (
                "https://raw.githubusercontent.com/robocorp/rpaframework/5d8f3db0e3fe5"
                "5396afccd987afaa1f389df2527/packages/main/tests/resources/documentai/"
                "signature-check.png"
            ),
        }
        return {
            "paths": paths,
            "urls": urls,
        }

    @staticmethod
    @pytest.fixture
    def signature_response():
        with open(DOCAI_DIR / "signature-recognize-response.json") as stream:
            return json.load(stream)

    @pytest.mark.parametrize(
        "source,field_ending",
        [
            # source type, reference source ending, query source ending
            ("paths", ("2Q==", "gg==")),
            ("urls", ("signature-license.jpg", "signature-check.png")),
        ],
    )
    @mock.patch("RPA.DocumentAI.Base64AI.requests")
    def test_get_matching_signatures(
        self, mock_requests, library, input_files, source, field_ending
    ):
        files = input_files[source]
        sigs = library.get_matching_signatures(
            files["driving-license"], files["payment-check"]
        )
        args, kwargs = mock_requests.post.call_args
        assert args == ("https://base64.ai/api/signature/recognize",)
        payload = kwargs["json"]
        suffix = "Image" if source == "paths" else "Url"
        assert payload[f"reference{suffix}"].endswith(field_ending[0])
        assert payload[f"query{suffix}"].endswith(field_ending[1])

    @pytest.mark.parametrize(
        "threshold,ref_idx,qry_idxes,similarities",
        [
            (0.8, 0, [0], [0.89]),  # only one accepted match for the first reference
            (0.5, 0, [0], [0.89]),  # still the same even when lowering thresholds
            (0.5, 1, [0, 1], [0.66, 0.61]),  # but different for the 2nd reference
        ],
    )
    def test_filter_matching_signatures(
        self, library, signature_response, threshold, ref_idx, qry_idxes, similarities
    ):
        matches = library.filter_matching_signatures(
            signature_response,
            confidence_threshold=threshold,
            similarity_threshold=threshold,
        )
        ref_key = [key for key in matches.keys() if key[0] == ref_idx][0]
        qry_imgs = matches[ref_key]
        assert len(qry_imgs) == len(qry_idxes) == len(similarities)

        for qry_idx, similarity in zip(qry_idxes, similarities):
            qry_img = [img for img in qry_imgs if img["index"] == qry_idx][0]
            assert qry_img["similarity"] == similarity

    @pytest.mark.parametrize(
        "index,reference,path,name,subcontent",
        [
            (0, False, None, "query-0.png", b"@@@@@@@@@@@@@@@@@@@@@@"),
            (0, True, RESULTS_DIR / "ref-sig.jpg", "ref-sig.jpg", b"(((((((((((((((("),
        ],
    )
    @mock.patch("RPA.DocumentAI.Base64AI.get_output_dir")
    def test_get_signature_image(
        self,
        mock_get_output_dir,
        library,
        signature_response,
        index,
        reference,
        path,
        name,
        subcontent,
    ):
        mock_get_output_dir.return_value = RESULTS_DIR
        image_path_str = library.get_signature_image(
            signature_response, index=index, reference=reference, path=path
        )
        image_path = Path(image_path_str)
        assert image_path.name == name
        assert subcontent in image_path.read_bytes()
