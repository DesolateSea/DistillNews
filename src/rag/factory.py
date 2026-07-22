"""
Factory for creating document store backends from configuration.
"""

import os
from config import config
from .base import DocumentStore


def create_doc_store(backend: str | None = None, **kwargs) -> DocumentStore:
    """Create a document store backend instance.

    Args:
        backend: Backend name. If *None*, reads from config (default: ``"julep"``).
        **kwargs: Extra keyword arguments forwarded to the backend
                  constructor.

    Returns:
        A :class:`DocumentStore` instance.

    Raises:
        ValueError: If the backend name is not recognised.
    """
    backend = backend or config.RAG_BACKEND

    if backend == "julep":
        from .backends.julep import JulepDocStore

        return JulepDocStore(**kwargs)
    elif backend == "none":
        from .backends.noop import NoOpDocStore

        return NoOpDocStore()
    else:
        raise ValueError(
            f"Unknown RAG backend: {backend!r}. "
            f"Available: julep, none"
        )
