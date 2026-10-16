from .paragraph_extractor import clean_html
from .reddit_parser import reddit_parser
from .rapid_news_parser import rapid_news_parser
from .gnews_parser import gnews_parser
from .media_stack_parser import media_stack_parser
try:
    from service.logger import log
except ImportError:
    log = None
import json

def reddit_handler(json_path, extract_news):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    total = len(data)
    for idx, post in enumerate(data, 1):
        title = (post.get("title") or "Untitled")[:50]
        log.info(f"[reddit] Item {idx}/{total}", title)
        extract_news(post, parser=reddit_parser, prompt="news_from_reddit_post.yaml", assured_news=False, raw_source_file=str(json_path))

def rapid_news_handler(json_path, extract_news):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert(data.get("status") == "OK")
    items = data.get("data", [])
    total = len(items)
    for idx, news in enumerate(items, 1):
        title = (news.get("title") or "Untitled")[:50]
        log.info(f"[rapid_news] Item {idx}/{total}", title)
        extract_news(news, parser=rapid_news_parser, prompt="news_from_html_type1.yaml", raw_source_file=str(json_path))

def gnews_handler(json_path, extract_news):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("articles", [])
    total = len(items)
    for idx, articles in enumerate(items, 1):
        title = (articles.get("title") or "Untitled")[:50]
        log.info(f"[gnews] Item {idx}/{total}", title)
        extract_news(articles, parser=gnews_parser, prompt="news_from_html_type1.yaml", raw_source_file=str(json_path))

def media_stack_handler(json_path, extract_news):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("data", [])
    total = len(items)
    for idx, news in enumerate(items, 1):
        title = (news.get("title") or "Untitled")[:50]
        log.info(f"[media_stack] Item {idx}/{total}", title)
        extract_news(news, parser=media_stack_parser, prompt="news_from_html_type1.yaml", raw_source_file=str(json_path))

api_handlers = {
    "reddit": reddit_handler,
    "rapid_news": rapid_news_handler,
    "gnews": gnews_handler,
    "media_stack": media_stack_handler,
}
