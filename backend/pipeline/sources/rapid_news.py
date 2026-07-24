import os
import json
import http.client
from datetime import datetime
from config import config

try:
    from pipeline.logger import log
except ImportError:
    log = None

class RapidNewsFetcher:
    def __init__(self):
        self.api_key = config.RAPIDAPI_KEY
        self.api_host = "real-time-news-data.p.rapidapi.com"
        self.base_path = "api_data/rapid_news"

    def fetch_news(self, category):
        """Fetch news for a specific category"""
        conn = http.client.HTTPSConnection(self.api_host)
        
        # Setting headers with the provided API key
        headers = {
            'x-rapidapi-key': self.api_key,
            'x-rapidapi-host': self.api_host
        }

        # Construct the endpoint URL using the category
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
            return json.loads(data.decode("utf-8"))
        except Exception as e:
            if log:
                log.fetch_fail("RapidNews", str(e))
            return None

    def save_data(self, category, data):
        """Save the fetched news data to a file"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        save_path = os.path.join(self.base_path, date_str, category)
        os.makedirs(save_path, exist_ok=True)
        
        # Save data as a JSON file
        file_path = os.path.join(save_path, "news.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        if log:
            log.save(file_path, f"Saved {category} data")


if __name__ == "__main__":
    # Instantiate the fetcher class and fetch news for all categories
    fetcher = RapidNewsFetcher()
    categories = [
        "WORLD",
        "NATIONAL",
        "BUSINESS",
        "TECHNOLOGY",
        "ENTERTAINMENT",
        "SPORTS",
        "SCIENCE",
        "HEALTH",
    ]
    for category in categories:        
        data = fetcher.fetch_news(category)
        if data:
            fetcher.save_data(category, data)
            if log:
                log.fetch_done("RapidNews", len(data.get("data", [])))
