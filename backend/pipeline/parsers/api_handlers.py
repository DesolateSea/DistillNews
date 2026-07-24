from .paragraph_extractor import clean_html
from .reddit_parser import reddit_parser
from .rapid_news_parser import rapid_news_parser
from .gnews_parser import gnews_parser
from .media_stack_parser import media_stack_parser
import json

def reddit_handler(json_path, extract_news):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for post in data:
        extract_news(post, parser=reddit_parser, prompt="news_from_reddit_post.yaml", assured_news=False)

def rapid_news_handler(json_path, extract_news):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert(data["status"] == "OK")
    for news in data["data"]:
        extract_news(news, parser=rapid_news_parser, prompt="news_from_html_type1.yaml")

def gnews_handler(json_path, extract_news):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for articles in data["articles"]:
        extract_news(articles, parser=gnews_parser, prompt="news_from_html_type1.yaml")

def media_stack_handler(json_path, extract_news):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for news in data["data"]:
        extract_news(news, parser=media_stack_parser, prompt="news_from_html_type1.yaml")

api_handlers = {
    "reddit": reddit_handler,
    "rapid_news": rapid_news_handler,
    "gnews": gnews_handler,
    "media_stack": media_stack_handler,
}
