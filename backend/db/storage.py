"""Unified Storage Repository for pipeline files and processed articles."""

import json
from pathlib import Path
from hashlib import sha256


class FileStore:
    """Repository handle encapsulating all disk and article operations.

    Provides a clean API for reading/writing pipeline artifacts (processed articles,
    raw HTML, API responses) and syncing with database collections.
    """

    _root_dir: Path = Path(__file__).resolve().parent.parent / "data"

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

    # --- Processed Article Methods ---

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
