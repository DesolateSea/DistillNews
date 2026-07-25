from pathlib import Path
from datetime import date
from db import FileStore

# Resolve base directory
BASE_DIR = Path(__file__).resolve().parent

# Config paths
CONFIG_DIR = BASE_DIR / "config"
INPUT_HTML_FILE  = CONFIG_DIR / "proxies.html"
PROXIES_JSON     = CONFIG_DIR / "proxies.json"
WORKING_JSON     = CONFIG_DIR / "working_proxies.json"
TARGET_URLS_JSON = CONFIG_DIR / "target_urls.json"

# Scrape output — raw data dir via FileStore (backend/data/raw)
BASE_SCRAPE_DIR = FileStore.raw_dir()

def get_scrape_folder(run_timestamp=None):
    timestamp_str = run_timestamp or FileStore.get_iso_timestamp()
    folder = BASE_SCRAPE_DIR / timestamp_str
    folder.mkdir(parents=True, exist_ok=True)
    return folder

# Test endpoint
CONNECT_TEST_URL = "https://httpbin.org/ip"
