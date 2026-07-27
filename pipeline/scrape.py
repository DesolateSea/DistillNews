"""
Scraping pipeline with parallel target URL crawling.

Reads target URLs from config and scrapes each one concurrently.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from service.db import FileStore
from config import config
from pipeline.scrapers.scraper import scrape_target
from pipeline.scrapers.config import TARGET_URLS_JSON
from service.logger import log

DEFAULT_SCRAPE_WORKERS = int(os.getenv("SCRAPE_PARALLEL_WORKERS", "5"))


def run_scrape(progress_callback=None, run_timestamp=None, max_workers=DEFAULT_SCRAPE_WORKERS):
    log.section(f"Parallel Web Scraping Pipeline (Workers: {max_workers})")

    if not config.is_source_enabled("scrape"):
        log.warn("Scraping service is disabled in pipeline configuration.")
        return

    targets = FileStore.read_json(TARGET_URLS_JSON)
    if not targets:
        log.warn("No scrape targets found.")
        return

    run_timestamp = run_timestamp or FileStore.get_iso_timestamp()

    tasks = []
    for category, urls in targets.items():
        for url in urls:
            tasks.append((category, url))

    total = len(tasks)
    log.info(f"Loaded {len(targets)} categories, {total} URLs total for parallel crawling")

    current = 0

    def _scrape_item(item):
        cat, u = item
        try:
            scrape_target(u, cat, run_timestamp=run_timestamp)
            return (cat, u, True, None)
        except Exception as e:
            return (cat, u, False, str(e))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_scrape_item, task): task for task in tasks}
        for future in as_completed(futures):
            current += 1
            cat, u, success, err = future.result()
            if progress_callback:
                progress_callback(current, max(total, 1), f"[{cat}] {u[:40]}")
            if success:
                log.info(f"[{current}/{total}] Scraped {cat}", u[:50])
            else:
                log.error(f"[{current}/{total}] Failed {cat} {u[:50]}", err)

    log.success("Parallel scraping pipeline complete")


if __name__ == "__main__":
    run_scrape()
