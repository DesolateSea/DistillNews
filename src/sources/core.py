from dotenv import load_dotenv
import requests
import json
import os
from datetime import datetime
load_dotenv()

CORE_API_KEY = os.getenv("CORE_API_KEY")

keywords = [
    "Artificial intelligence",
    "Computer science",
    "Technology",
    "Machine learning",
    "Physics",
    "Biology",
    "Chemistry",
    "Mathematics",
    "Bio technology",
    "Finance",
    "Cryptography",
    "Network",
    "Statistics",
    "Economics"
]

cur_date = datetime.now().strftime("%Y-%m-%d")
output_dir = f'api_data/core/{cur_date}'
os.makedirs(output_dir, exist_ok=True)

for keyword in keywords:
    r = requests.get(f"https://api.core.ac.uk/v3/search/works?q={keyword}&limit=20", headers={"Authorization": "Bearer " + CORE_API_KEY})
    results = r.json()["results"]
    papers = []
    for i in results:
        papers.append({
            "content": i["fullText"],
            "title": i["title"],
            "citationCount": i["citationCount"]
        })
    with open(f'api_data/core/{cur_date}/{keyword}.json', 'w+') as f:
        json.dump(papers, f, indent=4)
