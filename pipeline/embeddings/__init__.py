"""Provider-neutral text embedding layer.

Embedding generation is independent from both chat-completion providers and
document stores. The selected provider is read from ``EMBEDDING_PROVIDER``.
"""

from .base import EmbeddingProvider
from .factory import create_embedding_provider

__all__ = ["EmbeddingProvider", "create_embedding_provider"]
