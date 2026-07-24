"""
rag — Abstract document storage and retrieval layer.

Usage:
    from rag import create_doc_store

    store = create_doc_store()  # RAG_BACKEND=memory
    # EMBEDDING_PROVIDER selects OpenAI, Ollama, Hugging Face, or none.
    store.upload([Document(title="...", content="...")])
    results = store.search("query", limit=5)
"""

from .factory import create_doc_store
from .base import DocumentStore, Document, SearchResult

__all__ = ["create_doc_store", "DocumentStore", "Document", "SearchResult"]
