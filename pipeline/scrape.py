"""
Scraping & HTML Parsing Pipeline with instant cancellation support.

Scrapes target URLs directly in memory, parses clean HTML text, and stores
clean parsed JSON payloads into data/api_data/scraped/ (without writing raw HTML files).
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from service.db import FileStore
from config import config
from pipeline.scrapers.scraper import scrape_target
from pipeline.scrapers.config import TARGET_URLS_JSON
from pipeline.parsers.paragraph_extractor import clean_html
from service.logger import log

DEFAULT_SCRAPE_WORKERS = int(os.getenv("SCRAPE_PARALLEL_WORKERS", "5"))


def run_scrape(progress_callback=None, run_timestamp=None, max_workers=DEFAULT_SCRAPE_WORKERS, stop_checker=None):
    log.section(f"Scraping & HTML Parsing Pipeline (Workers: {max_workers})")

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
    log.info(f"Loaded {len(targets)} categories, {total} target URLs for parallel scraping & parsing")

    current = 0

    def _scrape_and_parse_item(item):
        if stop_checker and stop_checker():
            return (None, "Cancelled", False, "Cancelled")
        cat, url = item
        try:
            html_text = scrape_target(url, cat, run_timestamp=run_timestamp)
            if not html_text:
                return (cat, url, False, "Empty HTML content")

            parsed, _ = clean_html(html_text)
            if parsed and parsed.get("title") and parsed.get("title") != "Unknown Title":
                parsed["url"] = url
                parsed["category"] = cat
                article_id = FileStore.compute_article_id(parsed["title"], parsed.get("publication_date", "Unknown"))
                parsed["article_id"] = article_id

                rel_path = f"api_data/scraped/{run_timestamp}/{cat}/{article_id}.json"
                FileStore.write_json(rel_path, parsed)
                return (cat, url, True, None)
            return (cat, url, False, "Failed to parse clean content")
        except Exception as e:
            return (cat, url, False, str(e))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_scrape_and_parse_item, task): task for task in tasks}
        for future in as_completed(futures):
            if stop_checker and stop_checker():
                log.warn("Cancellation requested", "Stopping scraping worker threads immediately")
                executor.shutdown(wait=False, cancel_futures=True)
                break
            current += 1
            cat, u, success, err = future.result()
            if progress_callback:
                progress_callback(current, max(total, 1), f"[{cat}] {u[:40]}")
            if success:
                log.info(f"[{current}/{total}] Scraped & Parsed [{cat}]", u[:50])
            else:
                log.error(f"[{current}/{total}] Failed [{cat}] {u[:50]}", err)

    log.success("Scraping & HTML parsing pipeline complete")


if __name__ == "__main__":
    run_scrape()
