"""Unified Storage Repository for pipeline files and processed articles.

``FileStore`` provides low-level disk I/O for raw data, API responses and
temporary pipeline files.  It is *always* available regardless of which
article storage backend is active.

``FileArticleStore`` wraps the ``processed/`` directory with the
``ArticleStore`` ABC so it can be used interchangeably with Azure Blob
and other backends.
"""

import os
import json
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone

from service.db.article_store import ArticleStore


class FileStore:
    """Repository handle encapsulating all disk and article operations.

    Provides a clean API for reading/writing pipeline artifacts (processed articles,
    raw HTML, API responses) and syncing with database collections.
    """

    _root_dir: Path = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parent.parent.parent / "data"))

    @classmethod
    def get_root(cls) -> Path:
        return cls._root_dir

    @classmethod
    def processed_dir(cls) -> Path:
        p = cls._root_dir / "processed"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @classmethod
    def raw_dir(cls) -> Path:
        p = cls._root_dir / "raw"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @classmethod
    def api_data_dir(cls) -> Path:
        p = cls._root_dir / "api_data"
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

    # --- Generic JSON & Text File Methods ---

    @classmethod
    def read_json(cls, relative_or_abs_path: str | Path) -> dict | list:
        path = Path(relative_or_abs_path)
        if not path.is_absolute():
            path = cls._root_dir / path
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def write_json(cls, relative_or_abs_path: str | Path, data: dict | list) -> Path:
        path = Path(relative_or_abs_path)
        if not path.is_absolute():
            path = cls._root_dir / path
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return path

    @classmethod
    def write_text(cls, relative_or_abs_path: str | Path, content: str) -> Path:
        path = Path(relative_or_abs_path)
        if not path.is_absolute():
            path = cls._root_dir / path
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    @classmethod
    def read_text(cls, relative_or_abs_path: str | Path) -> str:
        path = Path(relative_or_abs_path)
        if not path.is_absolute():
            path = cls._root_dir / path
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    @classmethod
    def file_exists(cls, relative_or_abs_path: str | Path) -> bool:
        path = Path(relative_or_abs_path)
        if not path.is_absolute():
            path = cls._root_dir / path
        return path.exists()


class FileArticleStore(ArticleStore):
    """ArticleStore implementation backed by the local ``data/processed/`` directory.

    Delegates to ``FileStore`` class methods so the on-disk layout is identical
    to the legacy behaviour.
    """

    def article_exists(
        self, title_or_id: str, pub_date: str | int | float | None = None
    ) -> bool:
        return FileStore.article_exists(title_or_id, pub_date)

    def save_article(self, article_data: dict, article_id: str | None = None) -> str:
        if not article_id:
            article_id = self.compute_article_id(
                article_data.get("title", ""), article_data.get("publication_date", "")
            )
        self._ensure_created_at(article_data)
        FileStore.save_processed_article(article_data, article_id=article_id)
        return article_id

    def load_article(self, article_id: str) -> dict | None:
        return FileStore.load_processed_article(article_id)

    def list_articles(self) -> list[dict]:
        """Return lightweight metadata for every stored article."""
        results = []
        for filepath in FileStore.list_processed_files():
            try:
                data = FileStore.read_json(filepath)
                if isinstance(data, dict):
                    results.append({
                        "id": filepath.stem,
                        "title": data.get("title", "Untitled"),
                        "category": data.get("category", ""),
                        "publication_date": data.get("publication_date", ""),
                        "source": data.get("source", ""),
                    })
            except Exception:
                pass
        return results

    def load_all_articles(self) -> list[dict]:
        """Load the full content of every stored article."""
        articles = []
        for filepath in FileStore.list_processed_files():
            try:
                data = FileStore.read_json(filepath)
                if isinstance(data, dict):
                    data["id"] = filepath.stem
                    articles.append(data)
            except Exception:
                pass
        return articles
