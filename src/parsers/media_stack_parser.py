from datetime import datetime
from copy import deepcopy
from scrapers.scraper import scrape_target, cache_hit
from .paragraph_extractor import clean_html

def media_stack_parser(media_item, no_repeat=True):
    """
    Parse news items from Media Stack API format into the standard format used by the app
    Scrapes additional content if needed
    
    Args:
        media_item (dict): News item from the Media Stack API
        
    Returns:
        tuple: (formatted_item, original_item)
    """
    formatted = {}
    
    # Extract basic fields
    formatted["title"] = media_item.get("title", "Unknown")
    
    # Convert published_at to timestamp
    published_date = media_item.get("published_at")
    if published_date:
        try:
            dt = datetime.strptime(published_date, "%Y-%m-%dT%H:%M:%S%z")
            formatted["publication_date"] = int(dt.timestamp())
        except (ValueError, TypeError):
            formatted["publication_date"] = "Unknown"
    else:
        formatted["publication_date"] = "Unknown"
    
    # Handle content - scrape if needed beyond description
    content = media_item.get("description", "")
    if "url" in media_item and media_item["url"]:
        # Scrape the article content from the URL
        try:
            content = clean_html(scrape_target(media_item["url"]))
            if no_repeat and cache_hit[0]:
                print("Article already processed, skipping")
                return None, None
        except Exception as e:
            print(f"Error scraping content from {media_item['url']}: {e}")
            # If scraping fails, use the description as fallback
            if not content:
                content = media_item.get("description", "No content found")
    
    formatted["content"] = content
    
    # Handle authors - Media Stack has a single author field that might contain multiple names
    authors = []
    if media_item.get("author"):
        # Split by common separators to handle multiple authors in one string
        author_str = media_item["author"]
        if "," in author_str or " and " in author_str:
            # Replace " and " with "," for consistent splitting
            author_str = author_str.replace(" and ", ", ")
            authors = [a.strip() for a in author_str.split(",")]
        else:
            authors = [author_str]
    formatted["authors"] = authors or ["Anonymous"]
    
    # Add additional metadata
    formatted["source"] = media_item.get("source", "Unknown")
    formatted["image_url"] = media_item.get("image", "")
    formatted["url"] = media_item.get("url", "")
    formatted["category"] = media_item.get("category", "")
    formatted["language"] = media_item.get("language", "en")
    formatted["country"] = media_item.get("country", "")
    
    return formatted, deepcopy(formatted)
