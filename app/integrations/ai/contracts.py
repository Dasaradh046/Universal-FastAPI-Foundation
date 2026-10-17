"""
AI/LLM service contracts.

Defines the provider-independent interface for chat completions and
embeddings, plus request/response data models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol

from pydantic import BaseModel


class Message(BaseModel):
    """A single chat message."""

    role: str  # system, user, assistant, tool
    content: str


class ChatRequest(BaseModel):
    """A chat completion request."""

    messages: List[Message]
    model: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: bool = False
    metadata: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """A chat completion response."""

    content: str
    model: str
    usage: Optional[Dict[str, int]] = (
        None  # prompt_tokens, completion_tokens, total_tokens
    )
    finish_reason: Optional[str] = None
    provider_response: Optional[Dict[str, Any]] = None


class EmbeddingRequest(BaseModel):
    """An embedding request."""

    input: List[str]
    model: str


class EmbeddingResponse(BaseModel):
    """An embedding response."""

    embeddings: List[List[float]]
    model: str
    usage: Optional[Dict[str, int]] = None
    provider_response: Optional[Dict[str, Any]] = None


class AIProvider(Protocol):
    """Protocol defining the AI/LLM provider interface."""

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Generate a chat completion.

        Args:
            request: The chat request

        Returns:
            The chat response

        Raises:
            AIProviderError: If the completion fails
        """
        ...

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate embeddings for a list of inputs.

        Args:
            request: The embedding request

        Returns:
            The embedding response

        Raises:
            AIProviderError: If embedding generation fails
        """
        ...


class AIProviderError(Exception):
    """Exception raised when an AI provider operation fails."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        provider_error_code: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.provider_error_code = provider_error_code


class AIBaseService(ABC):
    """Abstract base class for AI services."""

    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        pass

    @abstractmethod
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        pass
