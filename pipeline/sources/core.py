import requests
from datetime import datetime
from config import config
from service.db import FileStore
from pipeline.sources.config import CORE_KEYWORDS

CORE_API_KEY = config.CORE_API_KEY


def run_core_fetch(run_timestamp=None):
    cur_date = run_timestamp or FileStore.get_iso_timestamp()

    for keyword in CORE_KEYWORDS:
        r = requests.get(
            f"https://api.core.ac.uk/v3/search/works?q={keyword}&limit=20",
            headers={"Authorization": "Bearer " + CORE_API_KEY},
        )
        results = r.json().get("results", [])
        papers = []
        for i in results:
            papers.append(
                {
                    "content": i.get("fullText", ""),
                    "title": i.get("title", ""),
                    "citationCount": i.get("citationCount", 0),
                }
            )

        rel_path = f"api_data/core/{cur_date}/{keyword}.json"
        FileStore.write_json(rel_path, papers)


if __name__ == "__main__":
    run_core_fetch()
