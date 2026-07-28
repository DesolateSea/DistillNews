import os
import random
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from fake_useragent import UserAgent

ua = UserAgent()
session = requests.Session()

def fetch_and_save_direct_and_via_proxy(target_url, working_urls, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    direct_html = session.get(
        target_url, headers={"User-Agent": ua.random},
        timeout=10, verify=False
    ).text
    with open(os.path.join(output_folder, "direct.html"), "w", encoding="utf-8") as f:
        f.write(direct_html)

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
            with open(os.path.join(output_folder, "via_proxy.html"), "w", encoding="utf-8") as f:
                f.write(via_html)
        except Exception:
            pass

def final_rotate_scrape(target_url, working_urls, output_folder):
    def get_proxy():
        url = random.choice(working_urls)
        return {"http": url, "https": url}

    html = None
    for _ in range(5):
        proxy = get_proxy()
        try:
            r = session.get(
                target_url,
                headers={"User-Agent": ua.random, "Host": urlparse(target_url).netloc},
                proxies=proxy,
                timeout=10,
                verify=False
            )
            if r.status_code == 200:
                html = r.text
                break
        except Exception:
            pass
        time.sleep(1)

    if html:
        os.makedirs(output_folder, exist_ok=True)
        with open(os.path.join(output_folder, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)

        soup = BeautifulSoup(html, "html.parser")
        titles = [t.get_text() for t in soup.find_all("title")]
        with open(os.path.join(output_folder, "titles.html"), "w", encoding="utf-8") as f:
            f.write("<html><body><ul>")
            for t in titles:
                f.write(f"<li>{t}</li>")
            f.write("</ul></body></html>")
