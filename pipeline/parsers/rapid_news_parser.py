from datetime import datetime, timezone
from pipeline.scrapers.scraper import scrape_target, cache_hit
from .paragraph_extractor import clean_html
from copy import deepcopy
from utils.logger import log


def rapid_news_parser(news_item, no_repeat=True):
    """Parse news items from rapid news API format into standard format."""
    formatted = {}

    formatted["title"] = news_item.get("title", "Unknown")

    published_date = news_item.get("published_datetime_utc")
    if published_date:
        try:
            dt = datetime.strptime(published_date, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
            formatted["publication_date"] = int(dt.timestamp())
        except (ValueError, TypeError):
            formatted["publication_date"] = "Unknown"
    else:
        formatted["publication_date"] = "Unknown"

    content = ""
    if "link" in news_item:
        try:
            content = clean_html(scrape_target(news_item["link"]))
            if no_repeat and cache_hit[0]:
                log.save_skip("Article already processed", news_item["link"])
                return None, None
        except Exception as e:
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
