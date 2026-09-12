from service.rag.providers.remote_embedding import RemoteEmbeddingProvider
from service.rag.backends.memory import InMemoryVectorStore
from service.rag.base import Document
from service.db import create_article_store

_store = None
_loaded = False

def _ensure_store():
    global _store, _loaded
    if _loaded:
        return
        
    embedder = RemoteEmbeddingProvider()
    _store = InMemoryVectorStore(embedder=embedder)
    
    article_store = create_article_store()
    articles = article_store.load_all_articles()
    
    documents = []
    for art in articles:
        content = art.get("content", art.get("markdown_content", ""))
        metadata = {
            "id": art.get("id", ""),
            "category": art.get("category", ""),
            "tags": art.get("tags", []),
            "summary": art.get("summary", ""),
            "publication_date": art.get("publication_date", "")
        }
        documents.append(Document(
            title=art.get("title", ""),
            content=content,
            metadata=metadata
        ))
        
    _store.upload(documents)
    _loaded = True

def search_news(query: str, limit: int = 5, category: str | None = None) -> list[dict]:
    _ensure_store()
    results = _store.search(query=query, limit=limit if not category else limit * 5)
    
    formatted_results = []
    for res in results:
        if category and res.metadata.get("category", "").lower() != category.lower():
            continue
            
        formatted_results.append({
            "id": res.metadata.get("id", ""),
            "title": res.title,
            "snippet": res.snippet,
            "category": res.metadata.get("category", ""),
            "score": res.score
        })
        
        if len(formatted_results) >= limit:
            break
            
    return formatted_results
