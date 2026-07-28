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


def gnews_parser(news_item, no_repeat=True):
    """Parse news items from GNews API format into standard format."""
    formatted = {}
    formatted["title"] = news_item.get("title", "Unknown")

    published_date = news_item.get("publishedAt") or news_item.get("published_date")
    formatted["publication_date"] = parse_date_timestamp(published_date)

    # Early exit if article already processed on disk BEFORE calling web scraper
    if no_repeat and formatted["title"] and formatted["title"] != "Unknown":
        from service.db import create_article_store, ArticleStore
        article_store = create_article_store()
        article_id = ArticleStore.compute_article_id(formatted["title"], formatted["publication_date"])
        if article_store.article_exists(article_id):
            if log:
                log.save_skip("Article already processed", article_id)
            return None, None

    content = news_item.get("content", "")
    description = news_item.get("description", "")

    if not content or "[chars]" in content:
        if "url" in news_item and news_item["url"]:
            try:
                content = clean_html(scrape_target(news_item["url"]))
                if no_repeat and cache_hit[0]:
                    if log:
                        log.save_skip("Article already processed", news_item["url"])
                    return None, None
            except Exception as e:
                if log:
                    log.parse_fail(news_item.get("title", "GNews Article"), str(e))
                if not content or "[chars]" in content:
                    content = description or "No content found"

    formatted["content"] = content

    source = news_item.get("source", {})
    formatted["source"] = source.get("name", "Unknown")

    formatted["authors"] = []
    formatted["image_url"] = news_item.get("image", "")
    formatted["url"] = news_item.get("url", "")

    return formatted, deepcopy(formatted)
