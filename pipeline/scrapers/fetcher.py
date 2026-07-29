import os
import random
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from fake_useragent import UserAgent

ua = UserAgent()
session = requests.Session()

def fetch_direct_and_via_proxy(target_url, working_urls):
    try:
        direct_html = session.get(
            target_url, headers={"User-Agent": ua.random},
            timeout=10, verify=False
        ).text
        if direct_html:
            return direct_html
    except Exception:
        pass

    if working_urls:
        proxy = working_urls[0]
        try:
            via_html = session.get(
                target_url,
                headers={"User-Agent": ua.random, "Host": urlparse(target_url).netloc},
                proxies={"https": proxy},
                timeout=10,
                verify=False
            ).text
            if via_html:
                return via_html
        except Exception:
            pass

    return None

def final_rotate_scrape(target_url, working_urls):
    def get_proxy():
        url = random.choice(working_urls)
        return {"http": url, "https": url}

    for _ in range(3):
        if not working_urls:
            break
        proxy = get_proxy()
        try:
            r = session.get(
                target_url,
                headers={"User-Agent": ua.random, "Host": urlparse(target_url).netloc},
                proxies=proxy,
                timeout=10,
                verify=False
            )
            if r.status_code == 200 and r.text:
                return r.text
        except Exception:
            pass
        time.sleep(0.5)

    return None
