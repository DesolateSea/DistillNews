"""
Abstract base class for document storage and retrieval backends.
"""

from abc import ABC, abstractmethod
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


class DocumentStore(ABC):
    """Abstract base for document storage and retrieval backends.

    Implementations may be backed by Julep's built-in doc API,
    a vector database (ChromaDB, Pinecone), or a simple in-memory store.
    """

    @abstractmethod
    def upload(self, documents: list[Document]) -> None:
        """Upload / index a batch of documents."""

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        """Search the store by text query.

        Args:
            query: Natural-language search query.
            limit: Maximum number of results to return.

        Returns:
            A list of :class:`SearchResult` objects, ordered by relevance.
        """
