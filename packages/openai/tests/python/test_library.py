from RPA.OpenAI import OpenAI
from unittest.mock import patch

@patch("openai.Completion.create")
def test_completion_create_without_result_format(mock):
    mock.return_value = {"choices": [{"text": "Hello World"}]}
    lib = OpenAI()
    response = lib.completion_create("Foobar")
    assert response == "Hello World"

@patch("openai.Completion.create")
def test_completion_create_result_format_json(mock):
    mock.return_value = {"choices": [{"text": "Hello World"}]}
    lib = OpenAI()
    response = lib.completion_create("Foobar", result_format="json")
    assert response == {"choices": [{"text": "Hello World"}]}

@patch("openai.Completion.create")
def test_completion_create_result_format_string(mock):
    mock.return_value = {"choices": [{"text": "Hello World"}]}
    lib = OpenAI()
    response = lib.completion_create("Foobar", result_format="string")
    assert response == "Hello World"

@patch("openai.Completion.create")
def test_completion_create_result_format_error(mock):
    mock.return_value = {"choices": [{"text": "Hello World"}]}
    lib = OpenAI()
    response = lib.completion_create("Foobar", result_format="missing_value")
    assert response == None

@patch("openai.Image.create")
def test_image_create_without_result_format(mock):
    mock.return_value = {"data": [{"url": "https://example.com"}, {"url": "https://robocorp.com"}]}
    lib = OpenAI()
    response = lib.image_create("Foobar")
    assert response == ["https://example.com", "https://robocorp.com"]

@patch("openai.Image.create")
def test_image_create_result_format_list(mock):
    mock.return_value = {"data": [{"url": "https://example.com"}, {"url": "https://robocorp.com"}]}
    lib = OpenAI()
    response = lib.image_create("Foobar", result_format="list")
    assert response == ["https://example.com", "https://robocorp.com"]

@patch("openai.Image.create")
def test_image_create_result_format_json(mock):
    mock.return_value = {"data": [{"url": "https://example.com"}, {"url": "https://robocorp.com"}]}
    lib = OpenAI()
    response = lib.image_create("Foobar", result_format="json")
    assert response == {"data": [{"url": "https://example.com"}, {"url": "https://robocorp.com"}]}

@patch("openai.Image.create")
def test_image_create_result_format_error(mock):
    mock.return_value = {"data": [{"url": "https://example.com"}, {"url": "https://robocorp.com"}]}
    lib = OpenAI()
    response = lib.image_create("Foobar", result_format="missing_value")
    assert response == None

@patch("openai.Image.create_variation")
def test_image_create_variation_without_result_format(mock):
    mock.return_value = {"data": [{"url": "https://example.com"}, {"url": "https://robocorp.com"}]}
    lib = OpenAI()
    response = lib.image_create_variation(__file__)
    assert response == ["https://example.com", "https://robocorp.com"]

@patch("openai.Image.create_variation")
def test_image_creat_variatione_result_format_list(mock):
    mock.return_value = {"data": [{"url": "https://example.com"}, {"url": "https://robocorp.com"}]}
    lib = OpenAI()
    response = lib.image_create_variation(__file__, result_format="list")
    assert response == ["https://example.com", "https://robocorp.com"]

@patch("openai.Image.create_variation")
def test_image_create_variation_result_format_json(mock):
    mock.return_value = {"data": [{"url": "https://example.com"}, {"url": "https://robocorp.com"}]}
    lib = OpenAI()
    response = lib.image_create_variation(__file__, result_format="json")
    assert response == {"data": [{"url": "https://example.com"}, {"url": "https://robocorp.com"}]}

@patch("openai.Image.create_variation")
def test_image_create_variation_result_format_error(mock):
    mock.return_value = {"data": [{"url": "https://example.com"}, {"url": "https://robocorp.com"}]}
    lib = OpenAI()
    response = lib.image_create_variation(__file__, result_format="missing_value")
    assert response == None

