import os
import json
from datetime import datetime
import urllib.request
from urllib.parse import urlencode
from dotenv import load_dotenv

class GNewsClient:
    def __init__(self, base_dir="api_data/gnews"):
        load_dotenv()
        self.api_key = os.getenv("GNEWS_API_KEY")
        if not self.api_key:
            raise ValueError("GNEWS_API_KEY not found in .env file.")
        self.base_url = "https://gnews.io/api/v4/search"
        self.base_dir = base_dir

    def _make_dir(self, query):
        date_str = datetime.now().strftime("%Y-%m-%d")
        path = os.path.join(self.base_dir, date_str, query.replace(" ", "_"))
        os.makedirs(path, exist_ok=True)
        return path

    def _save_to_file(self, path, filename, data):
        with open(os.path.join(path, filename), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def fetch_articles(self, q, lang='en', country='india', category=None, sources=None, pageSize=100, page=1):
        params = {
            "q": q,
            "lang": lang,
            "apikey": self.api_key,
            "max": pageSize,
            "country": country,
            "page": page
        }

        # GNews does not support mixing sources with category or country
        if sources:
            params.pop("country", None)
            params.pop("category", None)
            params["sources"] = sources
        elif category:
            params["category"] = category

        url = f"{self.base_url}?{urlencode(params)}"

        try:
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode("utf-8"))
                articles = data.get("articles", [])

                save_path = self._make_dir(q)
                self._save_to_file(save_path, "results.json", data)

                print(f"Saved {len(articles)} articles for query '{q}'")
                return articles
        except Exception as e:
            print(f"Error fetching articles: {e}")
            return []

if __name__ == "__main__":
    client = GNewsClient()

    QUERIES = [
        "indian economy",
        "india government policy",
        "india health",
        "india news",
        "india social news",
        "india technology science",
        "india travel culture",
        "indian economy",
        "india government policy",
        "india health",
        "india news",
        "india social news",
        "india technology science",
        "india travel culture",
    ]

    for query in QUERIES:
        print(f"Fetching articles for: {query}")
        articles = client.fetch_articles(query)
        print(f"Fetched {len(articles)} articles for query '{query}'")
