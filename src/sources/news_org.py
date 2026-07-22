import os
import json
from datetime import datetime
from newsapi import NewsApiClient
from dotenv import load_dotenv

class NewsFetcher:
    def __init__(self, base_dir="api_data"):
        load_dotenv()
        api_key = os.getenv("NEWS_API_KEY")
        if not api_key:
            raise ValueError("API key not found in .env")
        self.newsapi = NewsApiClient(api_key=api_key)
        self.base_dir = base_dir

    def _make_dir(self, org, topic):
        date_str = datetime.now().strftime("%Y-%m-%d")
        path = os.path.join(self.base_dir, org, date_str, topic)
        os.makedirs(path, exist_ok=True)
        return path

    def _save_to_file(self, path, filename, data):
        with open(os.path.join(path, filename), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def fetch_all_articles(self, topic, sources='', domains='', from_date=None, to_date=None,
                           language='en', sort_by='relevancy', page=1):
        from_date = from_date or datetime.now().strftime("%Y-%m-%d")
        to_date = to_date or datetime.now().strftime("%Y-%m-%d")
        articles = self.newsapi.get_everything(q=topic,
                                               sources=sources,
                                               domains=domains,
                                               from_param=from_date,
                                               to=to_date,
                                               language=language,
                                               sort_by=sort_by,
                                               page=page)
        org = "everything"
        save_path = self._make_dir(org, topic)
        self._save_to_file(save_path, 'everything.json', articles)
        return articles

if __name__ == "__main__":
    fetcher = NewsFetcher()

    TOPIC_KEYWORDS = {
        "government_policy": "india government policy",
        "markets_crypto": "india crypto market",
        "business_finance": "indian economy",
        "national_international_news": "india news",
        "tech_science_innovation": "india technology science",
        "health_medicine": "india health",
        "sports": "india sports",
        "travel_lifestyle_culture": "india travel culture",
        "regional_news": "india regional news",
        "community_social_news": "india social news",
        "fact_checking": "india fact checking",
    }

    for topic, keyword in TOPIC_KEYWORDS.items():
        print(f"Fetching articles for: {topic} -> '{keyword}'")
        fetcher.fetch_all_articles(topic=keyword)
