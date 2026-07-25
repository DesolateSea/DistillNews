from datetime import datetime
from newsapi import NewsApiClient
from config import config
from db import FileStore
from pipeline.sources.config import NEWS_ORG_TOPICS

from utils.logger import log


class NewsFetcher:
    def __init__(self, base_dir="api_data"):
        api_key = config.NEWS_API_KEY
        if not api_key:
            raise ValueError("API key not found in .env")
        self.newsapi = NewsApiClient(api_key=api_key)
        self.base_dir = base_dir

    def _get_save_path(self, org, topic):
        date_str = datetime.now().strftime("%Y-%m-%d")
        return f"{self.base_dir}/{org}/{date_str}/{topic}/everything.json"

    def fetch_all_articles(
        self,
        topic,
        sources="",
        domains="",
        from_date=None,
        to_date=None,
        language="en",
        sort_by="relevancy",
        page=1,
    ):
        from_date = from_date or datetime.now().strftime("%Y-%m-%d")
        to_date = to_date or datetime.now().strftime("%Y-%m-%d")

        if log:
            log.fetch_start("NewsAPI", topic)

        articles = self.newsapi.get_everything(
            q=topic,
            sources=sources,
            domains=domains,
            from_param=from_date,
            to=to_date,
            language=language,
            sort_by=sort_by,
            page=page,
        )
        org = "everything"
        save_path = self._get_save_path(org, topic)
        FileStore.write_json(save_path, articles)

        count = len(articles.get("articles", []))
        if log:
            log.fetch_done("NewsAPI", count)
        return articles


if __name__ == "__main__":
    fetcher = NewsFetcher()
    for topic, keyword in NEWS_ORG_TOPICS.items():
        fetcher.fetch_all_articles(topic=keyword)
