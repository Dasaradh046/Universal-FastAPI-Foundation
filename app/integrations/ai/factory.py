"""
AI service factory.
"""

from app.core.config import settings
from app.integrations.ai.contracts import AIProvider
from app.integrations.ai.providers.openai import OpenAIProvider


def get_ai_provider() -> AIProvider:
    """Factory function to get the configured AI provider.

    Returns:
        An instance of the configured AI provider

    Raises:
        ValueError: If the configured AI provider is not supported
    """
    provider = settings.AI_PROVIDER

    if provider == "openai":
        return OpenAIProvider()
    else:
        raise ValueError(f"Unsupported AI provider: {provider}")


__all__ = ["get_ai_provider"]
