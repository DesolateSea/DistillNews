"""
Article generation pipeline.

Iterates over API data files and runs the extraction pipeline on each.

Replaces the old ``src/julep/generate_articles.py``.
"""

from service.db import FileStore
from config import config
from pipeline.parsers.api_handlers import api_handlers
from pipeline.extraction import extract_news
from service.logger import log
from pathlib import Path

API_ROOT = FileStore.api_data_dir()


def generate_articles(api_root=API_ROOT, progress_callback=None):
    log.section("Article Generation Pipeline")

    all_files = []
    for api_name in api_handlers.keys():
        if not config.is_source_enabled(api_name):
            log.warn(f"Skipping disabled pipeline service: {api_name}")
            continue
        base_path = Path(api_root) / api_name
        if base_path.exists():
            json_files = list(base_path.rglob("*.json"))
            all_files.append((api_name, json_files))
        else:
            log.warn(f"No data directory for {api_name}", str(base_path))

    total = sum(len(files) for _, files in all_files)
    current = 0

    for api_name, json_files in all_files:
        log.subsection(f"{api_name}  ({len(json_files)} files)")
        func = api_handlers[api_name]
        for json_file in json_files:
            current += 1
            if progress_callback:
                progress_callback(current, max(total, 1), f"[{api_name}] {json_file.name}")
            log.info(f"Processing {api_name}", str(json_file.name))
            try:
                func(json_file, extract_news)
            except Exception as e:
                log.error(f"[{api_name}] {json_file.name}", str(e))

    log.success("Article generation complete")


if __name__ == "__main__":
    generate_articles()
