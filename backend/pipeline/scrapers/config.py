from pathlib import Path
from datetime import date

# Resolve base directory
BASE_DIR = Path(__file__).resolve().parent

# Config paths
CONFIG_DIR = BASE_DIR / "config"
INPUT_HTML_FILE  = CONFIG_DIR / "proxies.html"
PROXIES_JSON     = CONFIG_DIR / "proxies.json"
WORKING_JSON     = CONFIG_DIR / "working_proxies.json"
TARGET_URLS_JSON = CONFIG_DIR / "target_urls.json"

# Scrape output — data dir is at src/data/raw
BASE_SCRAPE_DIR = BASE_DIR.parent / "data" / "raw"
TODAY_STR = date.today().isoformat()
DATE_FOLDER = BASE_SCRAPE_DIR / TODAY_STR
DATE_FOLDER.mkdir(parents=True, exist_ok=True)

# Test endpoint
CONNECT_TEST_URL = "https://httpbin.org/ip"
