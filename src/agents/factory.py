"""
Factory for creating agent providers from configuration.
"""

import os
from .base import AgentProvider


def create_agent(provider: str | None = None, **kwargs) -> AgentProvider:
    """Create an agent provider instance.

    Args:
        provider: Provider name. If *None*, reads the ``AGENT_PROVIDER``
                  environment variable (default: ``"julep"``).
        **kwargs: Extra keyword arguments forwarded to the provider
                  constructor (e.g., ``model``, ``api_key``).

    Returns:
        An :class:`AgentProvider` instance.

    Raises:
        ValueError: If the provider name is not recognised.
    """
    provider = provider or os.getenv("AGENT_PROVIDER", "julep")
    print("Using provider:", provider)

    if provider == "julep":
        from .providers.julep import JulepAgent

        return JulepAgent(**kwargs)
    elif provider == "openai":
        from .providers.openai import OpenAIAgent

        return OpenAIAgent(**kwargs)
    else:
        raise ValueError(
            f"Unknown agent provider: {provider!r}. "
            f"Available: julep, openai"
        )
