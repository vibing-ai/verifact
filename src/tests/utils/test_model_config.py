"""
Tests for model configuration utilities.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.utils.model_config import (
    OPENROUTER_API_ENDPOINT,
    configure_openai_for_openrouter,
    get_api_key,
    get_model_name,
    get_model_settings,
    get_openrouter_headers,
    make_openrouter_request,
)


class TestModelConfig:
    """Test model configuration utilities."""

    def test_get_model_name_explicit(self):
        """Test get_model_name with explicit model name."""
        result = get_model_name(model_name="test/model")
        assert result == "test/model"

    def test_get_model_name_from_env(self, monkeypatch):
        """Test get_model_name from environment variable."""
        monkeypatch.setenv("CLAIM_DETECTOR_MODEL", "test/model-from-env")
        result = get_model_name(agent_type="claim_detector")
        assert result == "test/model-from-env"

    def test_get_model_name_default(self):
        """Test get_model_name default value."""
        result = get_model_name(agent_type="claim_detector")
        assert result == "qwen/qwen3-8b:free"  # Default from DEFAULT_MODELS

    def test_get_model_settings(self, monkeypatch):
        """Test get_model_settings."""
        monkeypatch.setenv("MODEL_TEMPERATURE", "0.5")
        monkeypatch.setenv("MODEL_MAX_TOKENS", "500")
        settings = get_model_settings()
        assert settings["temperature"] == 0.5
        assert settings["max_tokens"] == 500

    def test_get_api_key(self, monkeypatch):
        """Test get_api_key."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-api-key")
        key = get_api_key()
        assert key == "test-api-key"

    def test_get_api_key_missing(self, monkeypatch):
        """Test get_api_key when key is missing."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        with pytest.raises(ValueError):
            get_api_key()

    def test_get_openrouter_headers(self, monkeypatch):
        """Test get_openrouter_headers."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-api-key")
        monkeypatch.setenv("OPENROUTER_SITE_URL", "https://test.com")
        monkeypatch.setenv("OPENROUTER_SITE_NAME", "Test App")
        
        headers = get_openrouter_headers()
        
        assert headers["Authorization"] == "Bearer test-api-key"
        assert headers["HTTP-Referer"] == "https://test.com"
        assert headers["X-Title"] == "Test App"
        assert headers["Content-Type"] == "application/json"

    @patch("openai.api_key", None)
    @patch("openai.base_url", None)
    @patch("openai.default_headers", {})
    def test_configure_openai_for_openrouter(self, monkeypatch):
        """Test configure_openai_for_openrouter."""
        import openai
        
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-api-key")
        monkeypatch.setenv("OPENROUTER_SITE_URL", "https://test.com")
        monkeypatch.setenv("OPENROUTER_SITE_NAME", "Test App")
        
        configure_openai_for_openrouter()
        
        assert openai.api_key == "test-api-key"
        assert openai.base_url == OPENROUTER_API_ENDPOINT
        assert "HTTP-Referer" in openai.default_headers
        assert "X-Title" in openai.default_headers
        assert openai.default_headers["HTTP-Referer"] == "https://test.com"
        assert openai.default_headers["X-Title"] == "Test App"

    @patch("httpx.post")
    def test_make_openrouter_request(self, mock_post):
        """Test make_openrouter_request."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"result": "success"}
        mock_post.return_value = mock_response
        
        result = make_openrouter_request(
            url="https://test.com/api",
            payload={"test": "data"},
            headers={"Authorization": "Bearer test"}
        )
        
        mock_post.assert_called_once()
        assert result == {"result": "success"} 