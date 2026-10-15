import os
from bs4 import BeautifulSoup
from datetime import datetime
from config import config
try:
    from service.logger import log
except ImportError:
    log = None

def clean_html(html_input, debug=None):
    if debug is None:
        debug = config.DEBUG

    if not html_input:
        return {"title": "Unknown Title", "author": "Unknown Author", "publication_date": "Unknown", "content": ""}

    # Network content is always HTML, never an instruction to read a local file.
    soup = BeautifulSoup(str(html_input), 'html.parser')

    def get_meta(name):
        tag = soup.find("meta", attrs={"name": name})
        return tag["content"] if tag and tag.get("content") else None

    def get_property(prop):
        tag = soup.find("meta", attrs={"property": prop})
        return tag["content"] if tag and tag.get("content") else None

    title = get_property("og:title") or (soup.title.string.strip() if soup.title else "Unknown Title")
    author = get_meta("author") or "Unknown Author"
    date = get_property("article:published_time")

    if date:
        try:
            date = datetime.fromisoformat(date).isoformat()
        except ValueError:
            date = "Unknown"
    else:
        date = "Unknown"

    paragraphs = soup.find_all("p")
    content = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

    if debug:
        log.info("Cleaned HTML parsed", f"Title: {title} | Author: {author} | Date: {date}")

    parsed = {
        "title": title,
        "publication_date": date,
        "content": content  # Optional truncation
    }
    source = {
        "title": title,
        "author": author,
        "publication_date": date,
    }

    return parsed, source
