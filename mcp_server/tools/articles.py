from service.db import create_article_store

_article_store = None

def _get_store():
    global _article_store
    if _article_store is None:
        _article_store = create_article_store()
    return _article_store

def fetch_article(article_id: str) -> dict:
    store = _get_store()
    article = store.load_article(article_id)
    if not article:
        return {"error": f"Article with ID {article_id} not found."}
        
    return {
        "title": article.get("title", ""),
        "content": article.get("content", article.get("markdown_content", "")),
        "category": article.get("category", ""),
        "tags": article.get("tags", []),
        "summary": article.get("summary", ""),
        "publication_date": article.get("publication_date", "")
    }

def count_articles() -> dict:
    store = _get_store()
    # list_articles returns lightweight metadata for stored articles
    articles = store.list_articles()
    return {"total": len(articles)}
