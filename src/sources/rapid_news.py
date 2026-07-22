import os
import json
import http.client
from datetime import datetime
from dotenv import load_dotenv

class RapidNewsFetcher:
    def __init__(self):
        # Load API key from .env file
        load_dotenv()
        self.api_key = os.getenv("RAPIDAPI_KEY")
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
        
        try:
            conn.request("GET", endpoint, headers=headers)
            res = conn.getresponse()
            if res.status != 200:
                print(f"Failed to fetch {category}: HTTP {res.status}")
                return None
            data = res.read()
            return json.loads(data.decode("utf-8"))
        except Exception as e:
            print(f"Error fetching {category}: {e}")
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
        
        print(f"Saved data for {category} to {file_path}")


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
        print(f"Fetching category: {category}")
        data = fetcher.fetch_news(category)
        if data:
            fetcher.save_data(category, data)
