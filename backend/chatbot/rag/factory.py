"""Factory for creating document store backends from configuration."""

from config import config
from .base import DocumentStore


def create_doc_store(backend: str | None = None, **kwargs) -> DocumentStore:
    """Create a document store backend instance.

    Args:
        backend: Backend name. If *None*, reads from ``RAG_BACKEND``.
        **kwargs: Extra keyword arguments forwarded to the backend constructor.

    Returns:
        A :class:`DocumentStore` instance.
    """
    backend = (backend or config.RAG_BACKEND).lower()

    if backend == "julep":
        from .backends.julep import JulepDocStore

        return JulepDocStore(**kwargs)
    elif backend == "memory":
        from embeddings import create_embedding_provider
        from .backends.memory import InMemoryVectorStore

        embedder = kwargs.pop("embedder", None) or create_embedding_provider()
        return InMemoryVectorStore(embedder=embedder, **kwargs)
    elif backend == "bm25":
        from .backends.bm25 import BM25DocStore

        return BM25DocStore(**kwargs)
    elif backend == "none":
        return DocumentStore()
    else:
        raise ValueError(
            f"Unknown RAG backend: {backend!r}. "
            "Available: memory, bm25, julep, none"
        )
