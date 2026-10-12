"""Abstract base class for article storage backends.

Provides a unified interface for storing and retrieving processed news articles,
independent of the underlying storage mechanism (file system, Azure Blob, etc.).

The ``create_article_store`` factory reads ``ARTICLE_STORE_BACKEND`` from configuration
and returns the appropriate concrete implementation.
"""

from abc import ABC, abstractmethod
from hashlib import sha256
from datetime import datetime, timezone


class ArticleStore(ABC):
    """Backend-agnostic interface for processed article persistence.

    Concrete implementations include:
    * ``FileArticleStore``  — local filesystem (default, used by pipeline)
    * ``AzureBlobArticleStore`` — Azure Blob Storage
    """

    # --- Static Helpers (shared across all backends) ---

    @staticmethod
    def compute_article_id(title: str, pub_date: str | int | float) -> str:
        """Deterministic SHA-256 article ID from title + publication date."""
        key = str(title) + str(pub_date)
        return sha256(key.encode("utf-8")).hexdigest()

    @staticmethod
    def sanitize_article_data(data: object, seen: set[int] | None = None) -> object:
        """Deep-sanitize article dictionary, removing private keys and circular references."""
        if seen is None:
            seen = set()

        obj_id = id(data)
        if obj_id in seen:
            return None

        if isinstance(data, dict):
            seen.add(obj_id)
            cleaned = {}
            for k, v in data.items():
                if str(k).startswith("_"):
                    continue
                val = ArticleStore.sanitize_article_data(v, seen)
                if val is not None or v is None:
                    cleaned[k] = val
            seen.remove(obj_id)
            return cleaned
        elif isinstance(data, (list, tuple)):
            seen.add(obj_id)
            cleaned_list = []
            for item in data:
                val = ArticleStore.sanitize_article_data(item, seen)
                if val is not None or item is None:
                    cleaned_list.append(val)
            seen.remove(obj_id)
            return cleaned_list
        elif isinstance(data, (str, int, float, bool)) or data is None:
            return data
        else:
            return str(data)

    # --- Abstract Interface ---

    @abstractmethod
    def article_exists(
        self, title_or_id: str, pub_date: str | int | float | None = None
    ) -> bool:
        """Check whether an article with the given ID (or title+date) already exists."""
        ...

    @abstractmethod
    def save_article(self, article_data: dict, article_id: str | None = None) -> str:
        """Persist a processed article and return its article ID.

        If *article_id* is ``None`` it is computed from ``title`` and
        ``publication_date`` fields in *article_data*.
        """
        ...

    @abstractmethod
    def load_article(self, article_id: str) -> dict | None:
        """Load a single article by ID.  Returns ``None`` if not found."""
        ...

    @abstractmethod
    def list_articles(self, limit: int | None = None) -> list[dict]:
        """Return lightweight metadata for stored articles.

        Each dict MUST contain at least ``"id"`` and ``"title"`` keys.
        """
        ...

    @abstractmethod
    def load_all_articles(self, limit: int | None = None) -> list[dict]:
        """Load the full content of stored articles."""
        ...

    def save_articles_batch(self, articles_data: list[dict]) -> list[str]:
        """Save a batch of articles sequentially or in parallel, returning list of article IDs."""
        ids = []
        for art in articles_data:
            if isinstance(art, dict):
                ids.append(self.save_article(art))
        return ids

    # --- Default helpers ---

    def _ensure_created_at(self, article_data: dict) -> None:
        if "created_at" not in article_data:
            article_data["created_at"] = datetime.now(timezone.utc).isoformat()


def create_article_store(backend: str | None = None) -> ArticleStore:
    """Factory — instantiate an ArticleStore based on *backend* string.

    Accepted values:
    * ``"file"``  — local filesystem (default)
    * ``"azure"`` — Azure Blob Storage
    """
    from config import config

    backend = (backend or config.ARTICLE_STORE_BACKEND).strip().lower()

    if backend == "file":
        from service.blob.filestore import FileArticleStore
        return FileArticleStore()
    elif backend == "azure":
        from service.blob.azure_blob_store import AzureBlobArticleStore
        return AzureBlobArticleStore(
            connection_string=config.AZURE_STORAGE_CONNECTION_STRING,
            container_name=config.AZURE_BLOB_CONTAINER,
        )
    else:
        raise ValueError(
            f"Unknown ARTICLE_STORE_BACKEND: {backend!r}. "
            "Accepted values: 'file', 'azure'."
        )
