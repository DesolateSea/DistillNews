"""
Scraping pipeline.

Reads target URLs from config and scrapes each one.

Replaces the old ``src/julep/run_scrape.py``.
"""

import json
from scrapers.scraper import scrape_target
from scrapers.config import TARGET_URLS_JSON
from pipeline.logger import log

log.section("Web Scraping Pipeline")

with open(TARGET_URLS_JSON, "r", encoding="utf-8") as f:
    targets = json.load(f)

total = sum(len(urls) for urls in targets.values())
log.info(f"Loaded {len(targets)} categories, {total} URLs total")

for category, urls in targets.items():
    log.subsection(f"{category}  ({len(urls)} URLs)")
    for url in urls:
        scrape_target(url, category)

log.success("Scraping pipeline complete")
