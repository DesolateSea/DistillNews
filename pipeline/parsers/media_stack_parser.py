from datetime import datetime
from copy import deepcopy
from pipeline.scrapers.scraper import scrape_target, cache_hit
from .paragraph_extractor import clean_html
try:
    from service.logger import log
except ImportError:
    log = None


def media_stack_parser(media_item, no_repeat=True):
    """Parse news items from Media Stack API format into standard format."""
    formatted = {}

    formatted["title"] = media_item.get("title", "Unknown")

    published_date = media_item.get("published_at")
    if published_date:
        try:
            dt = datetime.strptime(published_date, "%Y-%m-%dT%H:%M:%S%z")
            formatted["publication_date"] = int(dt.timestamp())
        except (ValueError, TypeError):
            formatted["publication_date"] = "Unknown"
    else:
        formatted["publication_date"] = "Unknown"

    content = media_item.get("description", "")
    if "url" in media_item and media_item["url"]:
        try:
            content = clean_html(scrape_target(media_item["url"]))
            if no_repeat and cache_hit[0]:
                log.save_skip("Article already processed", media_item["url"])
                return None, None
        except Exception as e:
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
