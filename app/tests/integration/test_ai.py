"""
Tests for the AI/LLM provider adapters.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.ai.contracts import (
    AIProviderError,
    ChatRequest,
    ChatResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    Message,
)
from app.integrations.ai.providers.openai import OpenAIProvider


@pytest.fixture
def openai_provider():
    """Create an OpenAIProvider with a test API key."""
    with patch("app.integrations.ai.providers.openai.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = "sk-test-openai-key-123"
        mock_settings.OPENAI_MODEL = "gpt-4o-mini"
        return OpenAIProvider()


class TestOpenAIProvider:
    """Tests for the OpenAIProvider."""

    def test_provider_initialization(self, openai_provider):
        """OpenAIProvider initializes with API key."""
        assert openai_provider.api_key == "sk-test-openai-key-123"
        assert openai_provider.default_model == "gpt-4o-mini"

    def test_provider_requires_api_key(self):
        """OpenAIProvider raises ValueError when API key is missing."""
        with patch("app.integrations.ai.providers.openai.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = None
            mock_settings.OPENAI_MODEL = "gpt-4o-mini"
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                OpenAIProvider()

    @pytest.mark.asyncio
    async def test_chat_success(self, openai_provider):
        """A successful chat completion returns a ChatResponse."""
        mock_choice = AsyncMock()
        mock_choice.message.content = "Hello, world!"
        mock_choice.finish_reason = "stop"

        mock_usage = AsyncMock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 5
        mock_usage.total_tokens = 15

        mock_completion = AsyncMock()
        mock_completion.model = "gpt-4o-mini"
        mock_completion.choices = [mock_choice]
        mock_completion.usage = mock_usage
        mock_completion.id = "chatcmpl-test123"

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        openai_provider._client = mock_client

        request = ChatRequest(
            messages=[Message(role="user", content="Say hello")],
            model="gpt-4o-mini",
        )

        response = await openai_provider.chat(request)

        assert isinstance(response, ChatResponse)
        assert response.content == "Hello, world!"
        assert response.model == "gpt-4o-mini"
        assert response.finish_reason == "stop"
        assert response.usage == {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        }
        assert response.provider_response["provider"] == "openai"

    @pytest.mark.asyncio
    async def test_chat_failure(self, openai_provider):
        """A failed chat completion raises AIProviderError."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API error")
        )
        openai_provider._client = mock_client

        request = ChatRequest(
            messages=[Message(role="user", content="Hello")],
            model="gpt-4o-mini",
        )

        with pytest.raises(AIProviderError):
            await openai_provider.chat(request)

    @pytest.mark.asyncio
    async def test_embed_success(self, openai_provider):
        """A successful embedding request returns an EmbeddingResponse."""
        mock_data_item = AsyncMock()
        mock_data_item.embedding = [0.1, 0.2, 0.3]

        mock_usage = AsyncMock()
        mock_usage.prompt_tokens = 8
        mock_usage.total_tokens = 8

        mock_response = AsyncMock()
        mock_response.model = "text-embedding-3-small"
        mock_response.data = [mock_data_item]
        mock_response.usage = mock_usage
        mock_response.object = "list"

        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        openai_provider._client = mock_client

        request = EmbeddingRequest(
            input=["hello world"],
            model="text-embedding-3-small",
        )

        response = await openai_provider.embed(request)

        assert isinstance(response, EmbeddingResponse)
        assert response.embeddings == [[0.1, 0.2, 0.3]]
        assert response.model == "text-embedding-3-small"
        assert response.usage == {"prompt_tokens": 8, "total_tokens": 8}
        assert response.provider_response["provider"] == "openai"

    @pytest.mark.asyncio
    async def test_embed_failure(self, openai_provider):
        """A failed embedding request raises AIProviderError."""
        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(side_effect=Exception("API error"))
        openai_provider._client = mock_client

        request = EmbeddingRequest(input=["hello"], model="text-embedding-3-small")

        with pytest.raises(AIProviderError):
            await openai_provider.embed(request)


class TestAIContracts:
    """Tests for the AI data contracts."""

    def test_message(self):
        """Message can be created with role and content."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_chat_request_defaults(self):
        """ChatRequest defaults to non-streaming."""
        req = ChatRequest(messages=[Message(role="user", content="Hi")], model="gpt-4")
        assert req.stream is False
        assert req.temperature is None
        assert req.max_tokens is None

    def test_chat_response(self):
        """ChatResponse can be created."""
        resp = ChatResponse(content="Hi", model="gpt-4")
        assert resp.content == "Hi"
        assert resp.model == "gpt-4"

    def test_embedding_request(self):
        """EmbeddingRequest can be created."""
        req = EmbeddingRequest(input=["hello"], model="text-embedding-3-small")
        assert req.input == ["hello"]

    def test_embedding_response(self):
        """EmbeddingResponse can be created."""
        resp = EmbeddingResponse(
            embeddings=[[0.1, 0.2]], model="text-embedding-3-small"
        )
        assert resp.embeddings == [[0.1, 0.2]]

    def test_ai_provider_error(self):
        """AIProviderError can carry status code and provider code."""
        err = AIProviderError(
            "failed", status_code=401, provider_error_code="invalid_key"
        )
        assert str(err) == "failed"
        assert err.status_code == 401
        assert err.provider_error_code == "invalid_key"
