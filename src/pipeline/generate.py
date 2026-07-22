"""
Article generation pipeline.

Iterates over API data files and runs the extraction pipeline on each.

Replaces the old ``src/julep/generate_articles.py``.
"""

from parsers.api_handlers import api_handlers
from pipeline.extraction import extract_news
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent
API_ROOT = SRC_DIR / "data" / "api_data"

todo = [
    "reddit",
    "rapid_news",
    "gnews",
    "media_stack",
]


def generate_articles(api_root=API_ROOT):
    for api_name, func in api_handlers.items():
        if api_name not in todo:
            continue

        base_path = Path(api_root) / api_name

        if not base_path.exists():
            continue
        for json_file in base_path.rglob("*.json"):
            try:
                func(json_file, extract_news)
            except Exception as e:
                print(f"[ERROR] {api_name}: {json_file} -> {e}")


if __name__ == "__main__":
    generate_articles()
