"""
Article generation pipeline.

Iterates over API data files and runs the extraction pipeline on each.

Replaces the old ``src/julep/generate_articles.py``.
"""

from db import FileStore
from pipeline.parsers.api_handlers import api_handlers
from pipeline.extraction import extract_news
from pipeline.logger import log
from pathlib import Path

API_ROOT = FileStore.api_data_dir()

todo = [
    "reddit",
    "rapid_news",
    "gnews",
    "media_stack",
]


def generate_articles(api_root=API_ROOT):
    log.section("Article Generation Pipeline")

    for api_name, func in api_handlers.items():
        if api_name not in todo:
            continue

        base_path = Path(api_root) / api_name

        if not base_path.exists():
            log.warn(f"No data directory for {api_name}", str(base_path))
            continue

        json_files = list(base_path.rglob("*.json"))
        log.subsection(f"{api_name}  ({len(json_files)} files)")

        for json_file in json_files:
            log.info(f"Processing {api_name}", str(json_file.name))
            try:
                func(json_file, extract_news)
            except Exception as e:
                log.error(f"[{api_name}] {json_file.name}", str(e))

    log.success("Article generation complete")


if __name__ == "__main__":
    generate_articles()
