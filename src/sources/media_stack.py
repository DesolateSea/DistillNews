import os
import json
from datetime import datetime
from config import config

class MediaStack:
    def __init__(self, access_key: str = None, base_url: str = "http://api.mediastack.com/v1"):
        self.access_key = access_key or config.MEDIASTACK_API_KEY
        if not self.access_key:
            raise ValueError("MediaStack API key not found. Set MEDIASTACK_API_KEY in your .env file.")
        self.base_url = base_url

    def build_url(self, endpoint: str, **params) -> str:
        query = f"access_key={self.access_key}"
        for key, value in params.items():
            if isinstance(value, list):
                value = ",".join(value)
            query += f"&{key}={value}"
        return f"{self.base_url}/{endpoint}?{query}"

    def get_news(self, **filters):
        import requests
        url = self.build_url("news", **filters)
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"API Error: {response.status_code} - {response.text}")
        return response.json()

    def save_data(self, data: dict, topic: str, base_path: str = "api_data/Media_stack"):
        if "data" not in data or not data["data"]:
            print("No data to save.")
            return

        try:
            date_str = data["data"][0]["published_at"].split("T")[0]
        except Exception:
            date_str = datetime.utcnow().strftime("%Y-%m-%d")

        dir_path = os.path.join(base_path, date_str, topic)
        os.makedirs(dir_path, exist_ok=True)

        file_path = os.path.join(dir_path, "news.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        print(f"Data saved to {file_path}")

if __name__ == "__main__":
    categories = [
        "general",
        "business",
        "entertainment",
        "health",
        "science",
        "sports",
        "technology",
    ]

    stack = MediaStack()

    for category in categories:
        print(f"Fetching category: {category}")
        try:
            data = stack.get_news(categories=category)
            stack.save_data(data, topic=category)
        except Exception as e:
            print(f"Failed to fetch/save {category}: {e}")
