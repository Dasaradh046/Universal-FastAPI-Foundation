"""
OpenAI AI/LLM provider adapter.

Implements the ``AIProvider`` protocol using OpenAI's chat completions
and embeddings APIs.

OpenAI API reference: https://platform.openai.com/docs/api-reference
"""

from __future__ import annotations

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.ai.contracts import (
    AIProvider,
    AIProviderError,
    ChatRequest,
    ChatResponse,
    EmbeddingRequest,
    EmbeddingResponse,
)

logger = get_logger(__name__)


class OpenAIProvider(AIProvider):
    """OpenAI AI/LLM provider implementation."""

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.default_model = settings.OPENAI_MODEL or "gpt-4o-mini"

        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY must be configured for the OpenAI provider"
            )

        self._client = AsyncOpenAI(api_key=self.api_key)

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Generate a chat completion via OpenAI.

        Args:
            request: The chat request

        Returns:
            The chat response

        Raises:
            AIProviderError: If the completion fails
        """
        try:
            completion = await self._client.chat.completions.create(
                model=request.model or self.default_model,
                messages=[m.model_dump() for m in request.messages],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=request.stream,
            )

            choice = completion.choices[0]
            content = choice.message.content or ""

            usage = None
            if completion.usage:
                usage = {
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens,
                    "total_tokens": completion.usage.total_tokens,
                }

            logger.info(
                "OpenAI chat completion: model=%s finish_reason=%s",
                completion.model,
                choice.finish_reason,
            )

            return ChatResponse(
                content=content,
                model=completion.model,
                usage=usage,
                finish_reason=choice.finish_reason,
                provider_response={"provider": "openai", "id": completion.id},
            )

        except Exception as e:
            logger.error(f"OpenAI chat completion failed: {e}")
            raise AIProviderError(
                f"OpenAI chat completion failed: {str(e)}",
                provider_error_code=type(e).__name__,
            ) from e

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate embeddings via OpenAI.

        Args:
            request: The embedding request

        Returns:
            The embedding response

        Raises:
            AIProviderError: If embedding generation fails
        """
        try:
            response = await self._client.embeddings.create(
                model=request.model or self.default_model,
                input=request.input,
            )

            embeddings = [data.embedding for data in response.data]

            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            logger.info(
                "OpenAI embeddings: model=%s count=%d",
                response.model,
                len(embeddings),
            )

            return EmbeddingResponse(
                embeddings=embeddings,
                model=response.model,
                usage=usage,
                provider_response={"provider": "openai", "object": response.object},
            )

        except Exception as e:
            logger.error(f"OpenAI embeddings failed: {e}")
            raise AIProviderError(
                f"OpenAI embeddings failed: {str(e)}",
                provider_error_code=type(e).__name__,
            ) from e


__all__ = ["OpenAIProvider"]
