"""
Factory for creating agent providers from configuration.
"""

import os
from config import config
from .base import AgentProvider


def create_agent(provider: str | None = None, **kwargs) -> AgentProvider:
    """Create an agent provider instance.

    Args:
        provider: Provider name. If *None*, reads from config (default: ``"julep"``).
        **kwargs: Extra keyword arguments forwarded to the provider
                  constructor (e.g., ``model``, ``api_key``).

    Returns:
        An :class:`AgentProvider` instance.

    Raises:
        ValueError: If the provider name is not recognised.
    """
    provider = provider or config.AGENT_PROVIDER
    print("Using provider:", provider)

    if provider == "julep":
        from .providers.julep import JulepAgent

        return JulepAgent(**kwargs)
    elif provider == "openai":
        from .providers.openai import OpenAIAgent

        return OpenAIAgent(**kwargs)
    elif provider == "ollama":
        from .providers.ollama import OllamaAgent

        return OllamaAgent(**kwargs)
    elif provider in ("huggingface", "hf"):
        from .providers.huggingface import HuggingFaceAgent

        return HuggingFaceAgent(**kwargs)
    else:
        raise ValueError(
            f"Unknown agent provider: {provider!r}. "
            f"Available: julep, openai, ollama, huggingface"
        )
