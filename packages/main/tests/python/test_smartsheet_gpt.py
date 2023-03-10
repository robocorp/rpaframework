import pytest
import smartsheet
from unittest import mock


@pytest.fixture
def smartsheet_client(mocker):
    smartsheet_mock = mocker.patch("smartsheet.Smartsheet")
    yield smartsheet_mock.return_value


def mock_smartsheet_request(smartsheet_client, response_data):
    mocked_response = mock.MagicMock()
    mocked_response.to_dict.return_value = response_data
    smartsheet_client._request = mock.MagicMock(return_value=mocked_response)


def test_get_sheet(smartsheet_client, mocker):
    # Arrange
    sheet_id = 1234
    sheet_data = {"id": sheet_id, "name": "Test Sheet"}
    mock_smartsheet_request(smartsheet_client, sheet_data)

    # Act
    sheet = smartsheet_client.Sheets.get_sheet(sheet_id)

    # Assert
    assert sheet["id"] == sheet_id
    assert sheet["name"] == "Test Sheet"
