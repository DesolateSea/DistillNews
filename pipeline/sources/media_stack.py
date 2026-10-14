from datetime import datetime
from urllib.parse import urlencode, urlsplit
from config import config
from service.db import FileStore
from pipeline.sources.config import MEDIA_STACK_CATEGORIES

try:
    from service.logger import log
except ImportError:
    log = None


class MediaStack:
    def __init__(self, access_key: str = None, base_url: str = "https://api.mediastack.com/v1"):
        self.access_key = access_key or config.MEDIASTACK_API_KEY
        if not self.access_key:
            raise ValueError("MediaStack API key not found. Set MEDIASTACK_API_KEY in your .env file.")
        if urlsplit(base_url).scheme != "https":
            raise ValueError("MediaStack requires HTTPS")
        self.base_url = base_url

    def build_url(self, endpoint: str, **params) -> str:
        query = {"access_key": self.access_key}
        for key, value in params.items():
            if isinstance(value, list):
                value = ",".join(value)
            query[key] = value
        return f"{self.base_url}/{endpoint}?{urlencode(query)}"

    def get_news(self, **filters):
        import requests
        url = self.build_url("news", **filters)
        if log:
            log.fetch_start("MediaStack", str(filters))
        response = requests.get(url, timeout=15, allow_redirects=False)
        if response.status_code != 200:
            if log:
                log.fetch_fail("MediaStack", f"HTTP {response.status_code}")
            raise Exception(f"API Error: HTTP {response.status_code}")
        return response.json()

    def save_data(self, data: dict, topic: str, base_path: str = "api_data/Media_stack", run_timestamp=None):
        if "data" not in data or not data["data"]:
            if log:
                log.warn("No data to save", topic)
            return

        date_str = run_timestamp or FileStore.get_iso_timestamp()
        rel_path = f"{base_path}/{date_str}/{topic}/news.json"
        saved = FileStore.write_json(rel_path, data)

        if log:
            log.save(str(saved), f"Saved {len(data['data'])} articles")


if __name__ == "__main__":
    stack = MediaStack()

    for category in MEDIA_STACK_CATEGORIES:
        if log:
            log.fetch_start("MediaStack", category)
        try:
            data = stack.get_news(categories=category)
            stack.save_data(data, topic=category)
            if log:
                log.fetch_done("MediaStack", len(data.get("data", [])))
        except Exception as e:
            if log:
                log.fetch_fail("MediaStack", str(e))
