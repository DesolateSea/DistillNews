from datetime import datetime, timezone
from copy import deepcopy
from pipeline.scrapers.scraper import scrape_target, cache_hit
from .paragraph_extractor import clean_html
try:
    from service.logger import log
except ImportError:
    log = None


def gnews_parser(news_item, no_repeat=True):
    """Parse news items from GNews API format into standard format."""
    formatted = {}

    formatted["title"] = news_item.get("title", "Unknown")

    published_date = news_item.get("publishedAt")
    if published_date:
        try:
            dt = datetime.strptime(published_date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            formatted["publication_date"] = int(dt.timestamp())
        except (ValueError, TypeError):
            formatted["publication_date"] = "Unknown"
    else:
        formatted["publication_date"] = "Unknown"

    content = news_item.get("content", "")
    description = news_item.get("description", "")

    if not content or "[chars]" in content:
        if "url" in news_item and news_item["url"]:
            try:
                content = clean_html(scrape_target(news_item["url"]))
                if no_repeat and cache_hit[0]:
                    log.save_skip("Article already processed", news_item["url"])
                    return None, None
            except Exception as e:
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
