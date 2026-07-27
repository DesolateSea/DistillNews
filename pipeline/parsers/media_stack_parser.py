from datetime import datetime, timezone
from copy import deepcopy
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


def media_stack_parser(media_item, no_repeat=True):
    """Parse news items from Media Stack API format into standard format."""
    formatted = {}
    formatted["title"] = media_item.get("title", "Unknown")

    published_date = media_item.get("published_at") or media_item.get("publishedAt")
    formatted["publication_date"] = parse_date_timestamp(published_date)

    # Early exit if article already processed on disk BEFORE calling web scraper
    if formatted["title"] and formatted["title"] != "Unknown":
        from service.db import FileStore
        article_id = FileStore.compute_article_id(formatted["title"], formatted["publication_date"])
        if FileStore.article_exists(article_id):
            if log:
                log.save_skip("Article already processed", article_id)
            return None, None

    content = media_item.get("description", "")
    if "url" in media_item and media_item["url"]:
        try:
            content = clean_html(scrape_target(media_item["url"]))
            if no_repeat and cache_hit[0]:
                if log:
                    log.save_skip("Article already processed", media_item["url"])
                return None, None
        except Exception as e:
            if log:
                log.parse_fail(media_item.get("title", "MediaStack Article"), str(e))
            if not content:
                content = media_item.get("description", "No content found")

    formatted["content"] = content

    authors = []
    if media_item.get("author"):
        author_str = media_item["author"]
        if "," in author_str or " and " in author_str:
            author_str = author_str.replace(" and ", ", ")
            authors = [a.strip() for a in author_str.split(",")]
        else:
            authors = [author_str]
    formatted["authors"] = authors or ["Anonymous"]

    formatted["source"] = media_item.get("source", "Unknown")
    formatted["image_url"] = media_item.get("image", "")
    formatted["url"] = media_item.get("url", "")
    formatted["category"] = media_item.get("category", "")
    formatted["language"] = media_item.get("language", "en")
    formatted["country"] = media_item.get("country", "")

    return formatted, deepcopy(formatted)
