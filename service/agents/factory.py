"""
Factory for creating agent providers from configuration.
"""

from config import config
from .base import AgentProvider


def create_agent(provider: str | None = None, **kwargs) -> AgentProvider:
    """Create an agent provider instance.

    Args:
        provider: Provider name. If *None*, reads from config (default: ``"openai"``).
        **kwargs: Extra keyword arguments forwarded to the provider constructor.

    Returns:
        An :class:`AgentProvider` instance.

    Raises:
        ValueError: If the provider name is not recognized.
    """
    provider = provider or config.AGENT_PROVIDER

    if provider == "openai":
        from .providers.openai import OpenAIAgent

        return OpenAIAgent(**kwargs)
    elif provider == "ollama":
        import os
        from .providers.openai import OpenAIAgent
        kwargs.setdefault("api_key", "ollama")
        kwargs.setdefault("model", os.getenv("OLLAMA_MODEL", "llama3.2"))
        kwargs.setdefault("base_url", os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/") + "/v1")
        return OpenAIAgent(**kwargs)
    else:
        raise ValueError(
            f"Unknown agent provider: {provider!r}. "
            f"Available: openai, ollama"
        )
