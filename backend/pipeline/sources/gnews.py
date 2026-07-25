from datetime import datetime
import urllib.request
from urllib.parse import urlencode
from config import config
from db import FileStore
from pipeline.sources.config import GNEWS_QUERIES

from utils.logger import log


class GNewsClient:
    def __init__(self, base_dir="api_data/gnews"):
        self.api_key = config.GNEWS_API_KEY
        if not self.api_key:
            raise ValueError("GNEWS_API_KEY not found in .env file.")
        self.base_url = "https://gnews.io/api/v4/search"
        self.base_dir = base_dir

    def _get_save_path(self, query):
        date_str = datetime.now().strftime("%Y-%m-%d")
        return f"{self.base_dir}/{date_str}/{query.replace(' ', '_')}/results.json"

    def fetch_articles(
        self, q, lang="en", country="india", category=None, sources=None, pageSize=100, page=1
    ):
        params = {
            "q": q,
            "lang": lang,
            "apikey": self.api_key,
            "max": pageSize,
            "country": country,
            "page": page,
        }

        if sources:
            params.pop("country", None)
            params.pop("category", None)
            params["sources"] = sources
        elif category:
            params["category"] = category

        url = f"{self.base_url}?{urlencode(params)}"

        if log:
            log.fetch_start("GNews", q)

        try:
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode("utf-8"))
                articles = data.get("articles", [])

                save_path = self._get_save_path(q)
                FileStore.write_json(save_path, data)

                if log:
                    log.fetch_done("GNews", len(articles))
                return articles
        except Exception as e:
            if log:
                log.fetch_fail("GNews", str(e))
            return []


if __name__ == "__main__":
    import json
    client = GNewsClient()
    for query in GNEWS_QUERIES:
        client.fetch_articles(query)
