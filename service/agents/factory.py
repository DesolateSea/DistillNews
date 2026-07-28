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
    elif provider == "julep":
        from .providers.julep import JulepAgent

        return JulepAgent(**kwargs)
    else:
        raise ValueError(
            f"Unknown agent provider: {provider!r}. "
            f"Available: openai, julep"
        )
