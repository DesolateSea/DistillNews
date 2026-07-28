import json
import urllib3
import requests
from bs4 import BeautifulSoup
from .config import INPUT_HTML_FILE, PROXIES_JSON, WORKING_JSON, CONNECT_TEST_URL

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
session = requests.Session()

def parse_proxies_to_json():
    with open(INPUT_HTML_FILE, "r", encoding="utf-8") as f:
        html = "<table>" + f.read() + "</table>"
    soup = BeautifulSoup(html, "html.parser")

    proxies = []
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 8:
            continue
        proxies.append({
            "ip":           tds[0].get_text(strip=True),
            "port":         tds[1].get_text(strip=True),
            "country_code": tds[2].get_text(strip=True),
            "country":      tds[3].get_text(strip=True),
            "anonymity":    tds[4].get_text(strip=True),
            "google":       tds[5].get_text(strip=True),
            "https":        tds[6].get_text(strip=True).lower(),
            "last_checked": tds[7].get_text(strip=True),
        })
    with open(PROXIES_JSON, "w", encoding="utf-8") as f:
        json.dump(proxies, f, indent=2)

def load_working_proxies():
    with open(WORKING_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [f"http://{p['ip']}:{p['port']}" for p in data]
