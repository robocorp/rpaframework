from RPA.OpenAI import OpenAI
from unittest.mock import MagicMock

def test_completion_create_without_result_format():
    lib = OpenAI()
    lib.authorize_to_openai("test-api-key")

    # Mock the new client
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].text = "Hello World"

    lib.client.completions.create = MagicMock(return_value=mock_response)

    response = lib.completion_create("Foobar")
    assert response == "Hello World"

def test_completion_create_result_format_json():
    lib = OpenAI()
    lib.authorize_to_openai("test-api-key")

    # Mock the new client
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].text = "Hello World"
    mock_response.model_dump.return_value = {"choices": [{"text": "Hello World"}]}

    lib.client.completions.create = MagicMock(return_value=mock_response)

    response = lib.completion_create("Foobar", result_format="json")
    assert response == {"choices": [{"text": "Hello World"}]}

def test_completion_create_result_format_string():
    lib = OpenAI()
    lib.authorize_to_openai("test-api-key")

    # Mock the new client
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].text = "Hello World"

    lib.client.completions.create = MagicMock(return_value=mock_response)

    response = lib.completion_create("Foobar", result_format="string")
    assert response == "Hello World"

def test_completion_create_result_format_error():
    lib = OpenAI()
    lib.authorize_to_openai("test-api-key")

    # Mock the new client
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].text = "Hello World"

    lib.client.completions.create = MagicMock(return_value=mock_response)

    response = lib.completion_create("Foobar", result_format="missing_value")
    assert response == None

def test_image_create_without_result_format():
    lib = OpenAI()
    lib.authorize_to_openai("test-api-key")

    # Mock the new client
    mock_response = MagicMock()
    mock_response.data = [MagicMock(), MagicMock()]
    mock_response.data[0].url = "https://example.com"
    mock_response.data[1].url = "https://robocorp.com"

    lib.client.images.generate = MagicMock(return_value=mock_response)

    response = lib.image_create("Foobar")
    assert response == ["https://example.com", "https://robocorp.com"]

def test_image_create_result_format_list():
    lib = OpenAI()
    lib.authorize_to_openai("test-api-key")

    # Mock the new client
    mock_response = MagicMock()
    mock_response.data = [MagicMock(), MagicMock()]
    mock_response.data[0].url = "https://example.com"
    mock_response.data[1].url = "https://robocorp.com"

    lib.client.images.generate = MagicMock(return_value=mock_response)

    response = lib.image_create("Foobar", result_format="list")
    assert response == ["https://example.com", "https://robocorp.com"]

def test_image_create_result_format_json():
    lib = OpenAI()
    lib.authorize_to_openai("test-api-key")

    # Mock the new client
    mock_response = MagicMock()
    mock_response.data = [MagicMock(), MagicMock()]
    mock_response.data[0].url = "https://example.com"
    mock_response.data[1].url = "https://robocorp.com"
    mock_response.model_dump.return_value = {"data": [{"url": "https://example.com"}, {"url": "https://robocorp.com"}]}

    lib.client.images.generate = MagicMock(return_value=mock_response)

    response = lib.image_create("Foobar", result_format="json")
    assert response == {"data": [{"url": "https://example.com"}, {"url": "https://robocorp.com"}]}

def test_image_create_result_format_error():
    lib = OpenAI()
    lib.authorize_to_openai("test-api-key")

    # Mock the new client
    mock_response = MagicMock()
    mock_response.data = [MagicMock(), MagicMock()]
    mock_response.data[0].url = "https://example.com"
    mock_response.data[1].url = "https://robocorp.com"

    lib.client.images.generate = MagicMock(return_value=mock_response)

    response = lib.image_create("Foobar", result_format="missing_value")
    assert response == None

def test_image_create_variation_without_result_format():
    lib = OpenAI()
    lib.authorize_to_openai("test-api-key")

    # Mock the new client
    mock_response = MagicMock()
    mock_response.data = [MagicMock(), MagicMock()]
    mock_response.data[0].url = "https://example.com"
    mock_response.data[1].url = "https://robocorp.com"

    lib.client.images.create_variation = MagicMock(return_value=mock_response)

    response = lib.image_create_variation(__file__)
    assert response == ["https://example.com", "https://robocorp.com"]

def test_image_creat_variatione_result_format_list():
    lib = OpenAI()
    lib.authorize_to_openai("test-api-key")

    # Mock the new client
    mock_response = MagicMock()
    mock_response.data = [MagicMock(), MagicMock()]
    mock_response.data[0].url = "https://example.com"
    mock_response.data[1].url = "https://robocorp.com"

    lib.client.images.create_variation = MagicMock(return_value=mock_response)

    response = lib.image_create_variation(__file__, result_format="list")
    assert response == ["https://example.com", "https://robocorp.com"]

def test_image_create_variation_result_format_json():
    lib = OpenAI()
    lib.authorize_to_openai("test-api-key")

    # Mock the new client
    mock_response = MagicMock()
    mock_response.data = [MagicMock(), MagicMock()]
    mock_response.data[0].url = "https://example.com"
    mock_response.data[1].url = "https://robocorp.com"
    mock_response.model_dump.return_value = {"data": [{"url": "https://example.com"}, {"url": "https://robocorp.com"}]}

    lib.client.images.create_variation = MagicMock(return_value=mock_response)

    response = lib.image_create_variation(__file__, result_format="json")
    assert response == {"data": [{"url": "https://example.com"}, {"url": "https://robocorp.com"}]}

def test_image_create_variation_result_format_error():
    lib = OpenAI()
    lib.authorize_to_openai("test-api-key")

    # Mock the new client
    mock_response = MagicMock()
    mock_response.data = [MagicMock(), MagicMock()]
    mock_response.data[0].url = "https://example.com"
    mock_response.data[1].url = "https://robocorp.com"

    lib.client.images.create_variation = MagicMock(return_value=mock_response)

    response = lib.image_create_variation(__file__, result_format="missing_value")
    assert response == None


# Tests for new client API functionality
def test_completion_create_with_new_client():
    """Test completion using new client API"""
    lib = OpenAI()
    lib.authorize_to_openai("test-api-key")

    # Mock the new client
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].text = "Hello World"
    mock_response.model_dump.return_value = {"choices": [{"text": "Hello World"}]}

    lib.client.completions.create = MagicMock(return_value=mock_response)

    # Test string result format
    response = lib.completion_create("Test prompt", result_format="string")
    assert response == "Hello World"

    # Test json result format
    response = lib.completion_create("Test prompt", result_format="json")
    assert response == {"choices": [{"text": "Hello World"}]}


def test_chat_completion_create_with_new_client():
    """Test chat completion using new client API"""
    lib = OpenAI()
    lib.authorize_to_openai("test-api-key")

    # Mock the new client
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello from ChatGPT"

    lib.client.chat.completions.create = MagicMock(return_value=mock_response)

    response = lib.chat_completion_create("Hello", model="gpt-3.5-turbo")
    assert response[0] == "Hello from ChatGPT"
    assert len(response[1]) == 2  # user message + assistant response


def test_image_create_with_new_client():
    """Test image generation using new client API"""
    lib = OpenAI()
    lib.authorize_to_openai("test-api-key")

    # Mock the new client
    mock_response = MagicMock()
    mock_response.data = [MagicMock(), MagicMock()]
    mock_response.data[0].url = "https://example.com"
    mock_response.data[1].url = "https://robocorp.com"
    mock_response.model_dump.return_value = {"data": [{"url": "https://example.com"}, {"url": "https://robocorp.com"}]}

    lib.client.images.generate = MagicMock(return_value=mock_response)

    # Test list result format
    response = lib.image_create("Test prompt", result_format="list")
    assert response == ["https://example.com", "https://robocorp.com"]

    # Test json result format
    response = lib.image_create("Test prompt", result_format="json")
    assert response == {"data": [{"url": "https://example.com"}, {"url": "https://robocorp.com"}]}


def test_azure_openai_client_initialization():
    """Test Azure OpenAI client initialization"""
    lib = OpenAI()
    lib.authorize_to_azure_openai(
        api_key="test-key",
        api_base="https://test.openai.azure.com/",
        api_version="2023-05-15"
    )

    assert lib.service_type == "Azure"
    assert lib.client is not None

