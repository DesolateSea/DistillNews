"""
Article generation pipeline with 5 parallel worker threads and instant cancellation.

Unpacks individual article objects from API JSON files, allowing accurate
article-level progress estimation, 5-thread parallel LLM extraction,
and automatic resumption (skipping already-processed articles via URL, Title, and SHA-256 ID).
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import json
import os
from service.db import FileStore, create_article_store
from service.db.article_store import ArticleStore
from config import config
from pipeline.parsers.api_handlers import (
    reddit_parser,
    rapid_news_parser,
    gnews_parser,
    media_stack_parser
)
from pipeline.parsers.paragraph_extractor import clean_html
from pipeline.parsers.rapid_news_parser import parse_date_timestamp
from pipeline.extraction import extract_news
from service.logger import log

API_ROOT = FileStore.api_data_dir()
DEFAULT_WORKERS = int(os.getenv("PIPELINE_PARALLEL_WORKERS", "5"))

article_store = create_article_store()

# Dummy passthrough parser for already-parsed JSON payloads (e.g. scraped, core)
def passthrough_parser(item, no_repeat=True):
    return item, item

# Map API names to (parser_function, prompt_filename, news_items_key, assured_news)
API_CONFIGS = {
    "reddit": (reddit_parser, "news_from_reddit_post.yaml", None, False),
    "rapid_news": (rapid_news_parser, "news_from_html_type1.yaml", "data", True),
    "gnews": (gnews_parser, "news_from_html_type1.yaml", "articles", True),
    "media_stack": (media_stack_parser, "news_from_html_type1.yaml", "data", True),
    "core": (gnews_parser, "news_from_html_type1.yaml", None, True),
    "scraped": (passthrough_parser, "news_from_html_type1.yaml", None, True),
}


def find_api_directory(api_root: Path, api_name: str) -> Path | None:
    """Find a source directory case-insensitively (e.g. Media_stack -> media_stack)."""
    if not api_root.exists():
        return None
    target_clean = api_name.lower().replace("_", "")
    for child in api_root.iterdir():
        if child.is_dir():
            child_clean = child.name.lower().replace("_", "")
            if child_clean == target_clean:
                return child
    return None


def build_processed_index() -> tuple[set[str], set[str]]:
    """Build fast in-memory sets of all processed article URLs and lowercased titles."""
    existing_urls = set()
    existing_titles = set()

    for data in article_store.load_all_articles():
        try:
            if isinstance(data, dict):
                url = data.get("url") or data.get("link")
                if url:
                    existing_urls.add(str(url).strip())
                title = data.get("title")
                if title:
                    existing_titles.add(str(title).lower().strip())
        except Exception:
            pass

    return existing_urls, existing_titles


def is_already_processed_safe(raw_item: dict, existing_urls: set, existing_titles: set) -> bool:
    """Check if an article item is already on disk via assigned ID, URL, Title, or SHA-256 ID."""
    if raw_item.get("article_id") and article_store.article_exists(raw_item["article_id"]):
        return True

    url = raw_item.get("url") or raw_item.get("link")
    if url and str(url).strip() in existing_urls:
        return True

    title = raw_item.get("title") or raw_item.get("headline") or ""
    if title and str(title).lower().strip() in existing_titles:
        return True

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
        article_id = ArticleStore.compute_article_id(title, pub_date)
        if article_store.article_exists(article_id):
            return True

    return False


def load_article_items_from_file(api_name: str, json_path: Path, existing_urls: set, existing_titles: set) -> tuple[list[tuple], int]:
    """Read a JSON file and extract unprocessed article item tuples."""
    if api_name not in API_CONFIGS:
        return [], 0

    parser_func, prompt, items_key, assured = API_CONFIGS[api_name]
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if items_key is None:
            raw_items = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        else:
            if isinstance(data, dict):
                raw_items = data.get(items_key, [])
            else:
                raw_items = []

        item_tuples = []
        skipped_count = 0

        for raw_item in raw_items:
            if isinstance(raw_item, dict):
                if is_already_processed_safe(raw_item, existing_urls, existing_titles):
                    skipped_count += 1
                else:
                    item_tuples.append((api_name, parser_func, prompt, assured, raw_item, str(json_path)))

        return item_tuples, skipped_count
    except Exception as e:
        log.error(f"Error loading {json_path.name}", str(e))
        return [], 0


def generate_articles(api_root=API_ROOT, progress_callback=None, max_workers=DEFAULT_WORKERS, stop_checker=None):
    log.section(f"5-Thread Parallel LLM Article Generation (Workers: {max_workers})")

    existing_urls, existing_titles = build_processed_index()
    if existing_urls or existing_titles:
        log.info("Loaded processed article index", f"{len(existing_urls)} URLs, {len(existing_titles)} titles indexed")

    all_article_tasks = []
    total_skipped = 0
    api_root_path = Path(api_root)

    for api_name in API_CONFIGS.keys():
        if stop_checker and stop_checker():
            log.warn("Cancellation requested during pre-scan", "Aborting article generation")
            return

        if not config.is_source_enabled(api_name):
            log.warn(f"Skipping disabled pipeline service: {api_name}")
            continue
        
        base_path = find_api_directory(api_root_path, api_name)
        if base_path and base_path.exists():
            json_files = list(base_path.rglob("*.json"))
            for json_file in json_files:
                if stop_checker and stop_checker():
                    break
                file_items, skipped = load_article_items_from_file(api_name, json_file, existing_urls, existing_titles)
                all_article_tasks.extend(file_items)
                total_skipped += skipped
        else:
            log.warn(f"No data directory for {api_name}", str(api_root_path / api_name))

    total = len(all_article_tasks)
    if total_skipped > 0:
        log.info("Resume Check", f"{total_skipped} articles already processed (skipping), {total} remaining")

    if total == 0:
        log.success("All articles already processed", f"{total_skipped} total articles verified on disk")
        return

    log.info("Starting 5 parallel LLM extraction workers", f"{total} new articles queued")
    current = 0

    def _process_single_article(task):
        if stop_checker and stop_checker():
            return (None, "Cancelled", False, "Cancelled")
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
            if stop_checker and stop_checker():
                log.warn("Cancellation requested", "Stopping generation worker threads immediately")
                executor.shutdown(wait=False, cancel_futures=True)
                break
            current += 1
            api_name, title, success, err = future.result()
            if progress_callback:
                progress_callback(current, total, f"[{api_name}] {title}")
            if success:
                log.info(f"[{current}/{total}] LLM Processed [{api_name}]", title)
            else:
                log.error(f"[{current}/{total}] LLM Extraction error [{api_name}]", f"'{title}': {err}")

    log.success("5-Thread parallel LLM article generation complete", f"{total} new articles processed ({total_skipped} skipped)")


if __name__ == "__main__":
    generate_articles()
