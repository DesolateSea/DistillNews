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

    if backend == "memory":
        from .backends.memory import InMemoryVectorStore

        embedder = kwargs.pop("embedder", None)
        if embedder is None:
            try:
                from pipeline.embeddings import create_embedding_provider
                embedder = create_embedding_provider()
            except ImportError:
                from .providers.remote_embedding import RemoteEmbeddingProvider
                embedder = RemoteEmbeddingProvider()

        return InMemoryVectorStore(embedder=embedder, **kwargs)
    elif backend == "bm25":
        from .backends.bm25 import BM25DocStore

        return BM25DocStore(**kwargs)
    elif backend == "none":
        return DocumentStore()
    else:
        raise ValueError(
            f"Unknown RAG backend: {backend!r}. "
            "Available: memory, bm25, none"
        )
