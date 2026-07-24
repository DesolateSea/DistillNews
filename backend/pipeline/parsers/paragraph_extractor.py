from bs4 import BeautifulSoup
from datetime import datetime

def clean_html(html_path, debug=False):
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

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
        print("\nCleaned HTML:")
        print(f"Title: {title}")
        print(f"Author: {author}")
        print(f"Date: {date}")
        print(f"Content: {content}")

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
