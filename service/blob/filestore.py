"""Unified Storage Repository for pipeline files and processed articles.

``FileStore`` provides low-level disk I/O for raw data, API responses and
temporary pipeline files. It can be initialized with custom file paths.

``FileArticleStore`` wraps a target directory with the ``ArticleStore`` ABC
so it can be used interchangeably with Azure Blob and other backends.
"""

import os
import json
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone

from service.blob.article_store import ArticleStore


class FileStore:
    """Repository handle encapsulating disk and article operations.

    Provides a clean API for reading/writing pipeline artifacts (processed articles,
    raw HTML, API responses). Can be instantiated with custom file paths.
    """

    _default_root_dir: Path = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parent.parent.parent / "data"))

    def __init__(self, root_dir: str | Path | None = None):
        if root_dir is not None:
            self._root_dir = Path(root_dir)
        else:
            self._root_dir = self._default_root_dir

    @classmethod
    def get_root(cls) -> Path:
        return cls._default_root_dir

    @property
    def root_dir(self) -> Path:
        return self._root_dir

    @classmethod
    def processed_dir(cls) -> Path:
        p = cls._default_root_dir / "processed"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @classmethod
    def raw_dir(cls) -> Path:
        p = cls._default_root_dir / "raw"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @classmethod
    def api_data_dir(cls) -> Path:
        p = cls._default_root_dir / "api_data"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @classmethod
    def get_iso_timestamp(cls) -> str:
        """Returns an ISO 8601 UTC timestamp of start (e.g. '2026-07-25T11-30-48Z') formatted safely for directory names."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")

    # --- Processed Articles Repository ---

    @classmethod
    def compute_article_id(cls, title: str, pub_date: str | int | float) -> str:
        key = str(title) + str(pub_date)
        return sha256(key.encode("utf-8")).hexdigest()

    @classmethod
    def article_exists(
        cls, title_or_id: str, pub_date: str | int | float | None = None
    ) -> bool:
        if pub_date is not None:
            article_id = cls.compute_article_id(title_or_id, pub_date)
        else:
            article_id = title_or_id
        return (cls.processed_dir() / f"{article_id}.json").exists()

    @classmethod
    def save_processed_article(
        cls, article_data: dict, article_id: str | None = None
    ) -> Path:
        if not article_id:
            article_id = cls.compute_article_id(
                article_data.get("title", ""), article_data.get("publication_date", "")
            )
        if "created_at" not in article_data:
            article_data["created_at"] = datetime.now(timezone.utc).isoformat()

        filepath = cls.processed_dir() / f"{article_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(article_data, f, indent=2)
        return filepath

    @classmethod
    def load_processed_article(cls, article_id: str) -> dict | None:
        filepath = cls.processed_dir() / f"{article_id}.json"
        if not filepath.exists():
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def list_processed_files(cls) -> list[Path]:
        return sorted(cls.processed_dir().glob("*.json"))

    # --- Low-level JSON Helpers ---

    @classmethod
    def write_json(cls, filepath: Path, data: dict | list) -> Path:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return filepath

    @classmethod
    def read_json(cls, filepath: Path) -> dict | list | None:
        if not filepath.exists():
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)


class FileArticleStore(ArticleStore):
    """File-backed concrete implementation of ``ArticleStore``.

    Persists articles as JSON files in a local directory (defaults to ``data/processed/``).
    Can be initialized with custom file paths.
    """

    def __init__(self, processed_dir: str | Path | None = None):
        if processed_dir is not None:
            self._dir = Path(processed_dir)
        else:
            self._dir = FileStore.processed_dir()
        self._dir.mkdir(parents=True, exist_ok=True)

    def article_exists(
        self, title_or_id: str, pub_date: str | int | float | None = None
    ) -> bool:
        if pub_date is not None:
            article_id = self.compute_article_id(title_or_id, pub_date)
        else:
            article_id = title_or_id
        return (self._dir / f"{article_id}.json").exists()

    def save_article(self, article_data: dict, article_id: str | None = None) -> str:
        if not article_id:
            article_id = self.compute_article_id(
                article_data.get("title", ""),
                article_data.get("publication_date", ""),
            )

        article_data["id"] = article_id
        self._ensure_created_at(article_data)

        filepath = self._dir / f"{article_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(article_data, f, indent=2)

        return article_id

    def load_article(self, article_id: str) -> dict | None:
        filepath = self._dir / f"{article_id}.json"
        if not filepath.exists():
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data.setdefault("id", article_id)
            return data
        except Exception:
            return None

    def list_articles(self, limit: int | None = None) -> list[dict]:
        """Return lightweight metadata for stored articles."""
        summaries = []
        files = sorted(self._dir.glob("*.json"))
        if limit and limit > 0:
            files = files[:limit]
        for filepath in files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    summaries.append({
                        "id": data.get("id", filepath.stem),
                        "title": data.get("title", "Untitled"),
                        "category": data.get("category", "General"),
                        "publication_date": data.get("publication_date", ""),
                        "url": data.get("url", ""),
                        "source": data.get("source", {}),
                        "image_url": data.get("image_url") or data.get("image", ""),
                    })
            except Exception:
                continue
        return summaries

    def load_all_articles(self, limit: int | None = None) -> list[dict]:
        """Load the full content of stored articles."""
        articles = []
        files = sorted(self._dir.glob("*.json"))
        if limit and limit > 0:
            files = files[:limit]
        for filepath in files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("id", filepath.stem)
                    articles.append(data)
            except Exception:
                continue
        return articles
