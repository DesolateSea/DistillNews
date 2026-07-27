"""
Article generation pipeline with 5 parallel worker threads.

Unpacks individual article objects from API JSON files, allowing accurate
article-level progress estimation, 5-thread parallel web scraping & LLM extraction,
and automatic resumption (skipping already-processed articles without scraping).
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import json
import os
from service.db import FileStore
from config import config
from pipeline.parsers.api_handlers import (
    reddit_parser,
    rapid_news_parser,
    gnews_parser,
    media_stack_parser
)
from pipeline.parsers.rapid_news_parser import parse_date_timestamp
from pipeline.extraction import extract_news
from service.logger import log

API_ROOT = FileStore.api_data_dir()
DEFAULT_WORKERS = int(os.getenv("PIPELINE_PARALLEL_WORKERS", "5"))

# Map API names to (parser_function, prompt_filename, news_items_key, assured_news)
API_CONFIGS = {
    "reddit": (reddit_parser, "news_from_reddit_post.yaml", None, False),
    "rapid_news": (rapid_news_parser, "news_from_html_type1.yaml", "data", True),
    "gnews": (gnews_parser, "news_from_html_type1.yaml", "articles", True),
    "media_stack": (media_stack_parser, "news_from_html_type1.yaml", "data", True),
}


def is_already_processed_safe(raw_item: dict) -> bool:
    """Check if an article item is already on disk WITHOUT calling scrapers."""
    try:
        title = raw_item.get("title") or raw_item.get("headline") or ""
        date_raw = (
            raw_item.get("created_utc")
            or raw_item.get("publication_date")
            or raw_item.get("published_datetime_utc")
            or raw_item.get("publishedAt")
            or raw_item.get("published_at")
            or "Unknown"
        )
        pub_date = parse_date_timestamp(date_raw)
        if title and title != "Unknown":
            article_id = FileStore.compute_article_id(title, pub_date)
            return FileStore.article_exists(article_id)
    except Exception:
        pass
    return False


def load_article_items_from_file(api_name: str, json_path: Path) -> tuple[list[tuple], int]:
    """Read a JSON file and extract unprocessed article item tuples."""
    if api_name not in API_CONFIGS:
        return [], 0

    parser_func, prompt, items_key, assured = API_CONFIGS[api_name]
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if items_key is None:
            raw_items = data if isinstance(data, list) else []
        else:
            if isinstance(data, dict):
                raw_items = data.get(items_key, [])
            else:
                raw_items = []

        item_tuples = []
        skipped_count = 0

        for raw_item in raw_items:
            if isinstance(raw_item, dict):
                if is_already_processed_safe(raw_item):
                    skipped_count += 1
                else:
                    item_tuples.append((api_name, parser_func, prompt, assured, raw_item, str(json_path)))

        return item_tuples, skipped_count
    except Exception as e:
        log.error(f"Error loading {json_path.name}", str(e))
        return [], 0


def generate_articles(api_root=API_ROOT, progress_callback=None, max_workers=DEFAULT_WORKERS):
    log.section(f"5-Thread Parallel Article Generation & Web Scraping (Workers: {max_workers})")

    all_article_tasks = []
    total_skipped = 0

    for api_name in API_CONFIGS.keys():
        if not config.is_source_enabled(api_name):
            log.warn(f"Skipping disabled pipeline service: {api_name}")
            continue
        base_path = Path(api_root) / api_name
        if base_path.exists():
            json_files = list(base_path.rglob("*.json"))
            for json_file in json_files:
                file_items, skipped = load_article_items_from_file(api_name, json_file)
                all_article_tasks.extend(file_items)
                total_skipped += skipped
        else:
            log.warn(f"No data directory for {api_name}", str(base_path))

    total = len(all_article_tasks)
    if total_skipped > 0:
        log.info("Resume Check", f"{total_skipped} articles already processed (skipping), {total} remaining")

    if total == 0:
        log.success("All articles already processed", f"{total_skipped} total articles verified on disk")
        return

    log.info("Starting 5 parallel extraction & scraping workers", f"{total} new articles queued")
    current = 0

    def _process_single_article(task):
        api_name, parser_func, prompt, assured, raw_item, source_path = task
        title = (raw_item.get("title") or "Untitled")[:50]
        try:
            extract_news(
                raw_item,
                parser=parser_func,
                prompt=prompt,
                assured_news=assured,
                raw_source_file=source_path
            )
            return (api_name, title, True, None)
        except Exception as e:
            return (api_name, title, False, str(e))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process_single_article, task): task for task in all_article_tasks}
        for future in as_completed(futures):
            current += 1
            api_name, title, success, err = future.result()
            if progress_callback:
                progress_callback(current, total, f"[{api_name}] {title}")
            if success:
                log.info(f"[{current}/{total}] Scraped & Processed [{api_name}]", title)
            else:
                log.error(f"[{current}/{total}] Extraction error [{api_name}]", f"'{title}': {err}")

    log.success("5-Thread parallel article generation & scraping complete", f"{total} new articles processed ({total_skipped} skipped)")


if __name__ == "__main__":
    generate_articles()
