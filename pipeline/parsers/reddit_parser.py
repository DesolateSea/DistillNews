from datetime import datetime, timezone
from pipeline.scrapers.scraper import scrape_target, cache_hit
from .paragraph_extractor import clean_html

try:
    from service.logger import log
except ImportError:
    log = None


def parse_date_timestamp(date_val):
    """Robust date parser supporting ISO 8601 strings, UNIX timestamps, and fallbacks."""
    if not date_val:
        return "Unknown"
    if isinstance(date_val, (int, float)):
        return int(date_val)
    if isinstance(date_val, str) and date_val.replace(".", "", 1).isdigit():
        return int(float(date_val))
    if isinstance(date_val, str):
        try:
            dt = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
            return int(dt.timestamp())
        except Exception:
            pass
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                dt = datetime.strptime(date_val, fmt).replace(tzinfo=timezone.utc)
                return int(dt.timestamp())
            except Exception:
                pass
    return "Unknown"


def reddit_parser(post, no_repeat=True):
    formatted = {}
    formatted["title"] = post.get("title", "Unknown")

    created_utc = post.get("created_utc", "Unknown")
    formatted["publication_date"] = parse_date_timestamp(created_utc)

    # Early exit if article already processed on disk BEFORE calling web scraper
    if formatted["title"] and formatted["title"] != "Unknown":
        from service.db import FileStore
        article_id = FileStore.compute_article_id(formatted["title"], formatted["publication_date"])
        if FileStore.article_exists(article_id):
            if log:
                log.save_skip("Article already processed", article_id)
            return None, None

    if post.get("content", "") == "":
        if log:
            log.info("Reddit Parser", "No content in post, scraping URL: " + post.get("url", ""))
        post["content"] = clean_html(scrape_target(post.get("url", "")))
        if no_repeat and cache_hit[0]:
            if log:
                log.save_skip("Article already processed", post.get("url", ""))
            return None, None

    formatted["content"] = post.get("content", post.get("selftext", "No content found, not a news article"))
    formatted["authors"] = post.get("author", ["Anonymous"])
    if not isinstance(formatted["authors"], list):
        formatted["authors"] = [formatted["authors"]]
    formatted["source"] = "Reddit"
    formatted["image_url"] = post.get("thumbnail", "")
    formatted["url"] = post.get("url", "")

    return formatted, post
