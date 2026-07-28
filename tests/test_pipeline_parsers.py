"""Light unit tests for news ingestion pipeline parsers using pytest."""

import json
from pathlib import Path
from pipeline.parsers.gnews_parser import gnews_parser
from pipeline.parsers.media_stack_parser import media_stack_parser
from pipeline.parsers.rapid_news_parser import rapid_news_parser
from pipeline.parsers.reddit_parser import reddit_parser

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_gnews_parser():
    with open(FIXTURES_DIR / "gnews.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    formatted, source = gnews_parser(data[0], no_repeat=False)
    assert formatted is not None
    assert "EV policy" in formatted["title"]
    assert formatted["publication_date"] == 1714092817
    assert formatted["source"] == "CNBC"


def test_media_stack_parser():
    with open(FIXTURES_DIR / "media_stack.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    formatted, source = media_stack_parser(data[0], no_repeat=False)
    assert formatted is not None
    assert "ambassador to Japan" in formatted["title"]
    assert formatted["publication_date"] == 1744993882


def test_rapid_news_parser():
    with open(FIXTURES_DIR / "rapid_news.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    formatted, source = rapid_news_parser(data[0], no_repeat=False)
    assert formatted is not None
    assert "Bengaluru airport" in formatted["title"]
    assert formatted["publication_date"] == 1744983329


def test_reddit_parser():
    with open(FIXTURES_DIR / "reddit.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    formatted, source = reddit_parser(data[0], no_repeat=False)
    assert formatted is not None
    assert "Marriage" in formatted["title"]
    assert source["subreddit"] == "india"
