from datetime import datetime
from pipeline.scrapers.scraper import scrape_target, cache_hit
from .paragraph_extractor import clean_html
from copy import deepcopy

def rapid_news_parser(news_item, no_repeat=True):
    """
    Parse news items from rapid news API format into the standard format used by the app
    Scrapes additional content if needed
    
    Args:
        news_item (dict): News item from the API
    """

    formatted = {}
    
    # Extract basic fields
    formatted["title"] = news_item.get("title", "Unknown")
    
    # Convert UTC datetime string to timestamp if available
    published_date = news_item.get("published_datetime_utc")
    if published_date:
        try:
            dt = datetime.strptime(published_date, "%Y-%m-%dT%H:%M:%S.%fZ")
            formatted["publication_date"] = int(dt.timestamp())
        except (ValueError, TypeError):
            formatted["publication_date"] = "Unknown"
    else:
        formatted["publication_date"] = "Unknown"

    # Handle content - scrape if not present
    content = ""
    if "link" in news_item:
        # Scrape the article content from the URL
        try:
            content = clean_html(scrape_target(news_item["link"]))
            if no_repeat and cache_hit[0]:
                print("Article already processed, skipping")
                return None, None
        except Exception as e:
            print(f"Error scraping content from {news_item['link']}: {e}")
            content = news_item.get("snippet", "")
    else:
        content = news_item.get("snippet", "")
    
    # Use snippet as fallback if we couldn't get content
    if not content:
        content = news_item.get("snippet", "No content found")
        
    formatted["content"] = content
    
    # Add additional metadata that might be useful for the app
    formatted["authors"] = news_item.get("authors", [])
    formatted["source"] = news_item.get("source_name", "Unknown")
    formatted["image_url"] = news_item.get("photo_url")
    formatted["url"] = news_item.get("link", "")
    
    return formatted, deepcopy(formatted)
