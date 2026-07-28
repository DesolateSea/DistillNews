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


def rapid_news_parser(news_item, no_repeat=True):
    """Parse news items from rapid news API format into standard format."""
    formatted = {}
    formatted["title"] = news_item.get("title", "Unknown")

    published_date = news_item.get("published_datetime_utc") or news_item.get("published_at")
    formatted["publication_date"] = parse_date_timestamp(published_date)

    # Early exit if article already processed on disk BEFORE calling web scraper
    if formatted["title"] and formatted["title"] != "Unknown":
        from service.db import FileStore
        article_id = FileStore.compute_article_id(formatted["title"], formatted["publication_date"])
        if FileStore.article_exists(article_id):
            if log:
                log.save_skip("Article already processed", article_id)
            return None, None

    content = ""
    if "link" in news_item:
        try:
            content = clean_html(scrape_target(news_item["link"]))
            if no_repeat and cache_hit[0]:
                if log:
                    log.save_skip("Article already processed", news_item["link"])
                return None, None
        except Exception as e:
            if log:
                log.parse_fail(news_item.get("title", "RapidNews Article"), str(e))
            content = news_item.get("snippet", "")
    else:
        content = news_item.get("snippet", "")

    if not content:
        content = news_item.get("snippet", "No content found")

    formatted["content"] = content
    formatted["authors"] = news_item.get("authors", [])
    formatted["source"] = news_item.get("source_name", "Unknown")
    formatted["image_url"] = news_item.get("photo_url")
    formatted["url"] = news_item.get("link", "")

    return formatted, deepcopy(formatted)
