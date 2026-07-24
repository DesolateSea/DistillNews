from datetime import datetime, timezone
from copy import deepcopy
from pipeline.scrapers.scraper import scrape_target, cache_hit
from .paragraph_extractor import clean_html

def gnews_parser(news_item, no_repeat=True):
    """
    Parse news items from GNews API format into the standard format used by the app
    Scrapes additional content if needed
    
    Args:
        news_item (dict): News item from the GNews API
        
    Returns:
        tuple: (formatted_item, original_item)
    """
    formatted = {}
    
    # Extract basic fields
    formatted["title"] = news_item.get("title", "Unknown")
    
    # Convert publishedAt to timestamp
    published_date = news_item.get("publishedAt")
    if published_date:
        try:
            dt = datetime.strptime(published_date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            formatted["publication_date"] = int(dt.timestamp())
        except (ValueError, TypeError):
            formatted["publication_date"] = "Unknown"
    else:
        formatted["publication_date"] = "Unknown"
    
    # Handle content - scrape if needed beyond provided content
    content = news_item.get("content", "")
    description = news_item.get("description", "")
    
    # If content ends with "[XXX chars]" indicating it's truncated, or is empty
    if not content or "[chars]" in content:
        if "url" in news_item and news_item["url"]:
            # Scrape the article content from the URL
            try:
                content = clean_html(scrape_target(news_item["url"]))
                if no_repeat and cache_hit[0]:
                    print("Article already processed, skipping")
                    return None, None
            except Exception as e:
                print(f"Error scraping content from {news_item['url']}: {e}")
                # If scraping fails, use the existing content or description as fallback
                if not content or "[chars]" in content:
                    content = description or "No content found"
    
    formatted["content"] = content
    
    # Extract source information
    source = news_item.get("source", {})
    formatted["source"] = source.get("name", "Unknown")
    
    # Add additional metadata
    formatted["authors"] = []  # GNews API doesn't typically provide author information
    formatted["image_url"] = news_item.get("image", "")
    formatted["url"] = news_item.get("url", "")
    
    return formatted, deepcopy(formatted)
