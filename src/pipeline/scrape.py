"""
Scraping pipeline.

Reads target URLs from config and scrapes each one.

Replaces the old ``src/julep/run_scrape.py``.
"""

import json
from scrapers.scraper import scrape_target
from scrapers.config import TARGET_URLS_JSON

with open(TARGET_URLS_JSON, "r", encoding="utf-8") as f:
    targets = json.load(f)

for category, urls in targets.items():
    for url in urls:
        scrape_target(url, category)
