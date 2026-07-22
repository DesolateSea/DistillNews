from datetime import datetime
from scrapers.scraper import scrape_target, cache_hit
from .paragraph_extractor import clean_html

def reddit_parser(post, no_repeat=True):
    if post["content"] == "":
        print("No content found, check if url is news article")
        post["content"] = clean_html(scrape_target(post["url"]))
        if no_repeat and cache_hit[0]:
            print("Article already processed, skipping")
            return None, None

    formatted = {}

    formatted["title"] = post.get("title", "Unknown")
    
    # Handle the publication date - convert to timestamp if it's not already
    created_utc = post.get("created_utc", "Unknown")
    if isinstance(created_utc, str) and created_utc.replace('.', '', 1).isdigit():
        # If it's a string that represents a number, convert to int
        formatted["publication_date"] = int(float(created_utc))
    elif isinstance(created_utc, (int, float)):
        # If already a number, just use it
        formatted["publication_date"] = int(created_utc)
    else:
        formatted["publication_date"] = "Unknown"
        
    formatted["content"] = post.get("content", post.get("selftext", "No content found, not a news article"))
    
    # Add additional fields to match news_api_parser output
    formatted["authors"] = post.get("author", ["Anonymous"])
    if not isinstance(formatted["authors"], list):
        formatted["authors"] = [formatted["authors"]]
    formatted["source"] = "Reddit"
    formatted["image_url"] = post.get("thumbnail", "")
    formatted["url"] = post.get("url", "")

    return formatted, post
