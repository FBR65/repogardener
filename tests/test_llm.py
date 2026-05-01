"""Tests for LLM client."""
import pytest
from unittest.mock import patch, MagicMock

from repogardener.llm import LLMClient


def test_llm_client_defaults():
    client = LLMClient()
    assert client.provider == "ollama"
    assert client.model == "kimi-k2.6:cloud"


def test_llm_client_ollama_chat():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "Hello, world!"}
    mock_resp.raise_for_status = MagicMock()

    client = LLMClient(provider="ollama")
    with patch("repogardener.llm.httpx.post", return_value=mock_resp):
        result = client.chat("Hi", system="Be helpful")
    assert result == "Hello, world!"


def test_llm_client_openrouter_chat():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "Greetings!"}}]
    }
    mock_resp.raise_for_status = MagicMock()

    client = LLMClient(provider="openrouter")
    with patch("repogardener.llm.httpx.post", return_value=mock_resp), \
         patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
        result = client.chat("Hello", system="Be polite")
    assert result == "Greetings!"


def test_llm_client_provider_override():
    client = LLMClient(provider="openrouter", model="deepseek/deepseek-v4-flash")
    assert client.provider == "openrouter"
    assert client.model == "deepseek/deepseek-v4-flash"
