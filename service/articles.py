"""Shared article domain service module.

Provides unified article retrieval, personalization ranking, and pagination
for both server endpoints and pipeline operations.
Operating purely on ArticleStore with ZERO database dependencies.
"""

import json
from fastapi import HTTPException
from server.models.articles_model import DurationRequest, ArticleInDB, PaginatedArticlesResponse
from server.utils.recommendation import sort_articles, get_publication_timestamp
from service.blob import ArticleStore, create_article_store
from service.db import RedisHandle

try:
    from service.logger import log
except ImportError:
    log = None

article_store: ArticleStore = create_article_store()


def _strip_heavy_fields(doc: dict) -> dict:
    """Return a clean copy of the article dict with internal/heavy fields removed for feed list views."""
    clean_doc = dict(doc)
    for heavy_key in (
        "content", "markdown_content", "summary", "embedding", "vector", "raw_html", "raw",
        "prompt_used", "raw_source_file", "agent_provider", "authors", "media"
    ):
        clean_doc.pop(heavy_key, None)

    src = clean_doc.get("source")
    if isinstance(src, dict):
        clean_src = dict(src)
        for sub_key in ("content", "markdown_content", "raw_html", "raw", "authors", "prompt_used", "raw_source_file", "agent_provider"):
            clean_src.pop(sub_key, None)
        clean_src.setdefault("media", [])
        clean_doc["source"] = clean_src
    elif isinstance(src, list):
        if src and isinstance(src[0], dict):
            clean_src = dict(src[0])
            for sub_key in ("content", "markdown_content", "raw_html", "raw", "authors", "prompt_used", "raw_source_file", "agent_provider"):
                clean_src.pop(sub_key, None)
            clean_src.setdefault("media", [])
            clean_doc["source"] = clean_src
        else:
            clean_doc["source"] = {"name": "Unknown", "media": []}
    elif isinstance(src, str):
        clean_doc["source"] = {"name": src, "media": []}
    else:
        clean_doc["source"] = {"name": "Unknown", "media": []}

    return clean_doc


async def _get_raw_articles() -> list[dict]:
    """Fetch article pool directly from article_store (Azure Blob or FileStore) sorted by publication date."""
    raw = article_store.load_all_articles()
    cleaned = [_strip_heavy_fields(art) if isinstance(art, dict) else art for art in raw]
    cleaned.sort(key=get_publication_timestamp, reverse=True)
    return cleaned


async def get_all_articles(user_profile: dict | None = None):
    """
    Return top 20 articles in decreasing order of publication time.
    If user_profile is provided, applies personalized category recommendation scores.
    """
    # Check Redis cache for default unauthenticated feed
    if not user_profile:
        try:
            cached_feed = await RedisHandle.client().get("cache:feed:default")
            if cached_feed:
                return json.loads(cached_feed)
        except Exception:
            pass

    raw_articles = await _get_raw_articles()

    if not user_profile:
        sorted_by_date = sorted(raw_articles, key=get_publication_timestamp, reverse=True)
        res = {"feeds": sorted_by_date[:20]}
        try:
            await RedisHandle.client().set("cache:feed:default", json.dumps(res), ex=300)
        except Exception:
            pass
        return res

    preferences = user_profile.get("preferences", [])
    raw_weights = user_profile.get("bias", {})
    interactions = user_profile.get("category_scores", {cat: (0, 0.0) for cat in preferences})

    personalized = sort_articles(preferences, raw_weights, interactions, raw_articles)
    top20 = personalized[:20]
    return {"feeds": top20}


async def get_article_by_id(article_id: str):
    """
    Fetch complete article details (including full text content) for single article view.
    Uses Redis cache with a 10-minute TTL.
    """
    cache_key = f"cache:article:detail:{article_id}"
    try:
        cached_article = await RedisHandle.client().get(cache_key)
        if cached_article:
            return json.loads(cached_article)
    except Exception:
        pass

    article = article_store.load_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    article["popularity"] = article.get("popularity", 0) + 1
    if "_id" in article:
        article["_id"] = str(article["_id"])
    else:
        article["_id"] = article_id

    try:
        await RedisHandle.client().set(cache_key, json.dumps(article), ex=600)
    except Exception:
        pass

    return article


async def get_all_articles_pagination(
    user_profile: dict | None = None,
    page: int = 1,
    limit: int = 20,
) -> PaginatedArticlesResponse:
    skip = (page - 1) * limit

    raw = await _get_raw_articles()

    if user_profile:
        prefs = user_profile.get("preferences", [])
        weights = user_profile.get("bias", {})
        interactions = user_profile.get("category_scores", {c: (0, 0.0) for c in prefs})
        sorted_list = sort_articles(prefs, weights, interactions, raw)
    else:
        sorted_list = sorted(raw, key=get_publication_timestamp, reverse=True)

    paged = sorted_list[skip : skip + limit]
    total = len(sorted_list)
    has_more = (skip + len(paged)) < total

    return {
        "page": page,
        "limit": limit,
        "has_more": has_more,
        "total": total,
        "feeds": paged,
    }
