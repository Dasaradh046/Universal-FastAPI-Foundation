"""
AI service layer.
"""

from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.integrations.ai.contracts import (
    ChatRequest,
    ChatResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    Message,
)
from app.integrations.ai.factory import get_ai_provider

logger = get_logger(__name__)


class AIService:
    """Service for AI/LLM operations (chat, embeddings)."""

    def __init__(self):
        self.provider = get_ai_provider()

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatResponse:
        """Generate a chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Model name (uses provider default if not specified)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            metadata: Additional metadata

        Returns:
            The chat response

        Raises:
            AIProviderError: If the completion fails
        """
        chat_messages = [Message(**m) for m in messages]

        request = ChatRequest(
            messages=chat_messages,
            model=model or "",
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            metadata=metadata,
        )

        return await self.provider.chat(request)

    async def embed(
        self,
        input: List[str],
        model: Optional[str] = None,
    ) -> EmbeddingResponse:
        """Generate embeddings for a list of inputs.

        Args:
            input: List of text strings to embed
            model: Embedding model name (uses provider default if not specified)

        Returns:
            The embedding response

        Raises:
            AIProviderError: If embedding generation fails
        """
        request = EmbeddingRequest(input=input, model=model or "")

        return await self.provider.embed(request)


__all__ = ["AIService"]
