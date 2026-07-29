from urllib.parse import urlparse
from .proxies import load_working_proxies
from .fetcher import fetch_direct_and_via_proxy, final_rotate_scrape

# Import logger — use try/except so the module works standalone too
try:
    from service.logger import log
except ImportError:
    log = None

working_urls = load_working_proxies()

cache_hit = [False]

def scrape_target(target_url, category="default", run_timestamp=None):
    cache_hit[0] = False

    if log:
        log.scrape_start(target_url, "in-memory")

    html_content = fetch_direct_and_via_proxy(target_url, working_urls)
    if not html_content:
        html_content = final_rotate_scrape(target_url, working_urls)

    return html_content or ""
