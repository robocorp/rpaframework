"""Testing of RPA.DocumentAI library."""


import pytest
from unittest import mock

from RPA.DocumentAI import DocumentAI
from RPA.DocumentAI.Base64AI import Base64AI
from RPA.DocumentAI.DocumentAI import EngineName
from RPA.DocumentAI.Nanonets import Nanonets

from . import RESOURCES_DIR


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
        args, kwargs = mock_requests.request.call_args
        assert args == ("POST", "https://base64.ai/api/scan")
        assert model in kwargs["data"]

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
