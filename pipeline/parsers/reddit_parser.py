from datetime import datetime
from pipeline.scrapers.scraper import scrape_target, cache_hit
from .paragraph_extractor import clean_html
from utils.logger import log


def reddit_parser(post, no_repeat=True):
    if post["content"] == "":
        log.info("Reddit Parser", "No content in post, scraping URL: " + post["url"])
        post["content"] = clean_html(scrape_target(post["url"]))
        if no_repeat and cache_hit[0]:
            log.save_skip("Article already processed", post["url"])
            return None, None

    formatted = {}

    formatted["title"] = post.get("title", "Unknown")

    created_utc = post.get("created_utc", "Unknown")
    if isinstance(created_utc, str) and created_utc.replace(".", "", 1).isdigit():
        formatted["publication_date"] = int(float(created_utc))
    elif isinstance(created_utc, (int, float)):
        formatted["publication_date"] = int(created_utc)
    else:
        formatted["publication_date"] = "Unknown"

    formatted["content"] = post.get("content", post.get("selftext", "No content found, not a news article"))

    formatted["authors"] = post.get("author", ["Anonymous"])
    if not isinstance(formatted["authors"], list):
        formatted["authors"] = [formatted["authors"]]
    formatted["source"] = "Reddit"
    formatted["image_url"] = post.get("thumbnail", "")
    formatted["url"] = post.get("url", "")

    return formatted, post
