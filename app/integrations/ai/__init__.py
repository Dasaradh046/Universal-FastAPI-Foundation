"""
AI integration package.
"""

from app.integrations.ai.contracts import (
    AIProviderError,
    ChatRequest,
    ChatResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    Message,
)
from app.integrations.ai.factory import get_ai_provider
from app.integrations.ai.service import AIService

__all__ = [
    "get_ai_provider",
    "AIService",
    "Message",
    "ChatRequest",
    "ChatResponse",
    "EmbeddingRequest",
    "EmbeddingResponse",
    "AIProviderError",
]
