import http.client
from datetime import datetime
from config import config
from db import FileStore
from pipeline.sources.config import RAPID_NEWS_SECTIONS

from utils.logger import log


class RapidNewsFetcher:
    def __init__(self):
        self.api_key = config.RAPIDAPI_KEY
        self.api_host = "real-time-news-data.p.rapidapi.com"
        self.base_path = "api_data/rapid_news"

    def fetch_news(self, category):
        """Fetch news for a specific category"""
        conn = http.client.HTTPSConnection(self.api_host)

        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.api_host,
        }

        endpoint = f"/topic-news-by-section?topic={category.upper()}&limit=500&country=IN&lang=en"

        if log:
            log.fetch_start("RapidNews", category)

        try:
            conn.request("GET", endpoint, headers=headers)
            res = conn.getresponse()
            if res.status != 200:
                if log:
                    log.fetch_fail("RapidNews", f"HTTP {res.status} for {category}")
                return None
            data = res.read()
            import json

            return json.loads(data.decode("utf-8"))
        except Exception as e:
            if log:
                log.fetch_fail("RapidNews", str(e))
            return None

    def save_data(self, category, data):
        """Save the fetched news data using FileStore"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        rel_path = f"{self.base_path}/{date_str}/{category}/news.json"
        saved = FileStore.write_json(rel_path, data)

        if log:
            log.save(str(saved), f"Saved {category} data")


if __name__ == "__main__":
    fetcher = RapidNewsFetcher()
    for category in RAPID_NEWS_SECTIONS:
        data = fetcher.fetch_news(category)
        if data:
            fetcher.save_data(category, data)
            if log:
                log.fetch_done("RapidNews", len(data.get("data", [])))
