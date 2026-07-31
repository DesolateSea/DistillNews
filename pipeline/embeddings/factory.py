"""Factory for independent embedding providers."""

from config import config
from .base import EmbeddingProvider


def create_embedding_provider(
    provider: str | None = None, **kwargs
) -> EmbeddingProvider:
    """Create an embedding provider selected independently from the chatbot.

    Args:
        provider: Provider name. If omitted, reads ``EMBEDDING_PROVIDER``.
        **kwargs: Provider-specific constructor options.
    """
    provider = (provider or config.EMBEDDING_PROVIDER).lower()

    if provider in ("openai", "foundry"):
        from .providers.openai import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider(**kwargs)
    if provider in ("sentence_transformers", "sentence-transformers", "st"):
        from .providers.sentence_transformers import SentenceTransformersEmbeddingProvider

        return SentenceTransformersEmbeddingProvider(**kwargs)
    if provider in ("remote", "embedding_server", "http"):
        from .providers.remote import RemoteEmbeddingProvider

        return RemoteEmbeddingProvider(**kwargs)
    if provider == "none":
        return EmbeddingProvider()

    raise ValueError(
        f"Unknown embedding provider: {provider!r}. "
        "Available: openai, foundry, sentence_transformers, remote, none"
    )
