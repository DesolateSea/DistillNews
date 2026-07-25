import os
from urllib.parse import urlparse
from .config import get_scrape_folder
from .proxies import load_working_proxies
from .fetcher import fetch_and_save_direct_and_via_proxy, final_rotate_scrape

# Import logger — use try/except so the module works standalone too
from utils.logger import log

working_urls = load_working_proxies()

cache_hit = [False]

def scrape_target(target_url, category="default", run_timestamp=None):
    cache_hit[0] = False

    host = urlparse(target_url).netloc.replace(":", "_")
    target_folder = os.path.join(get_scrape_folder(run_timestamp), category, host)

    if log:
        log.scrape_start(target_url, target_folder)

    html_path = os.path.join(target_folder, "direct.html")
    if os.path.exists(html_path):
        if log:
            log.scrape_skip(target_url)
        cache_hit[0] = True
        return html_path

    fetch_and_save_direct_and_via_proxy(target_url, working_urls, target_folder)
    final_rotate_scrape(target_url, working_urls, target_folder)

    if log:
        log.save(html_path, "Scraped & saved")

    return html_path
