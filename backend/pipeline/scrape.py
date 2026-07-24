"""
Scraping pipeline.

Reads target URLs from config and scrapes each one.

Replaces the old ``src/julep/run_scrape.py``.
"""

from db import FileStore
from pipeline.scrapers.scraper import scrape_target
from pipeline.scrapers.config import TARGET_URLS_JSON
from pipeline.logger import log

def run_scrape():
    log.section("Web Scraping Pipeline")

    targets = FileStore.read_json(TARGET_URLS_JSON)

    total = sum(len(urls) for urls in targets.values())
    log.info(f"Loaded {len(targets)} categories, {total} URLs total")

    for category, urls in targets.items():
        log.subsection(f"{category}  ({len(urls)} URLs)")
        for url in urls:
            scrape_target(url, category)

    log.success("Scraping pipeline complete")


if __name__ == "__main__":
    run_scrape()

