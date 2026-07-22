"""
No-op document store backend.

Returns empty results for all operations. Useful when RAG is not needed
or when testing agent completions without a document store.
"""

from rag.base import DocumentStore, Document, SearchResult


class NoOpDocStore(DocumentStore):
    """DocumentStore that does nothing — for when RAG is disabled."""

    def upload(self, documents: list[Document]) -> None:
        """No-op."""

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        """Always returns an empty list."""
        return []
