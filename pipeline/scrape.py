"""
Scraping pipeline.

Reads target URLs from config and scrapes each one.

Replaces the old ``src/julep/run_scrape.py``.
"""

<<<<<<< HEAD:backend/pipeline/scrape.py
from db import FileStore
from config import config
from pipeline.scrapers.scraper import scrape_target
from pipeline.scrapers.config import TARGET_URLS_JSON
from utils.logger import log
=======
from service.db import FileStore
from pipeline.scrapers.scraper import scrape_target
from pipeline.scrapers.config import TARGET_URLS_JSON
from service.logger import log
>>>>>>> 582a92f (refactor: The code base has sperated the pipelines completely from the):pipeline/scrape.py

def run_scrape(progress_callback=None, run_timestamp=None):
    log.section("Web Scraping Pipeline")

    if not config.is_source_enabled("scrape"):
        log.warn("Scraping service is disabled in pipeline configuration.")
        return

    targets = FileStore.read_json(TARGET_URLS_JSON)
    if not targets:
        log.warn("No scrape targets found.")
        return

    run_timestamp = run_timestamp or FileStore.get_iso_timestamp()

    total = sum(len(urls) for urls in targets.values())
    log.info(f"Loaded {len(targets)} categories, {total} URLs total")

    current = 0
    for category, urls in targets.items():
        log.subsection(f"{category}  ({len(urls)} URLs)")
        for url in urls:
            current += 1
            if progress_callback:
                progress_callback(current, max(total, 1), f"[{category}] {url}")
            scrape_target(url, category, run_timestamp=run_timestamp)

    log.success("Scraping pipeline complete")


if __name__ == "__main__":
    run_scrape()

