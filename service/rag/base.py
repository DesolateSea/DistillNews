"""Base class for document storage and retrieval backends with default no-op behavior."""

from dataclasses import dataclass, field


@dataclass
class Document:
    """A document to be stored in the document store."""

    title: str
    content: str
    metadata: dict | None = field(default_factory=dict)


@dataclass
class SearchResult:
    """A single result returned from a document search."""

    title: str
    content: str
    snippet: str = ""
    score: float | None = None
    metadata: dict = field(default_factory=dict)


class DocumentStore:
    """Base class for document storage and retrieval backends.

    By default, returns empty search results when RAG is disabled.
    """

    def upload(self, documents: list[Document]) -> None:
        """Upload / index a batch of documents."""

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        """Search the store by text query.

        Args:
            query: Natural-language search query.
            limit: Maximum number of results to return.

        Returns:
            A list of :class:`SearchResult` objects, ordered by relevance.
        """
        return []


class EmbeddingProvider:
    """Base interface for embedding providers."""

    def embed(self, text: str) -> list[float]:
        """Generate a vector embedding for a single string."""
        return []

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        """Generate vector embeddings for a batch of strings."""
        return [self.embed(text) for text in texts]

