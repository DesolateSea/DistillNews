import json
from fastapi import HTTPException
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from server.models.articles_model import DurationRequest, ArticleInDB, PaginatedArticlesResponse
from server.utils.recommendation import sort_articles, update_weights, get_publication_timestamp
from service.db import MongoHandle, RedisHandle, create_article_store

try:
    from service.logger import log
except ImportError:
    log = None

scheduler = AsyncIOScheduler()
article_store = create_article_store()


def _strip_heavy_fields(doc: dict) -> dict:
    """Return a clean copy of the article dict with internal/heavy fields removed for feed list views."""
    clean_doc = dict(doc)
    # Remove internal metadata and heavy payload fields from feed responses
    for heavy_key in (
        "content", "markdown_content", "summary", "embedding", "vector", "raw_html", "raw",
        "prompt_used", "raw_source_file", "agent_provider", "authors", "media"
    ):
        clean_doc.pop(heavy_key, None)

    # Clean nested source object to strip source.content and internal source fields
    src = clean_doc.get("source")
    if isinstance(src, dict):
        clean_src = dict(src)
        for sub_key in ("content", "markdown_content", "raw_html", "raw", "authors", "prompt_used", "raw_source_file", "agent_provider", "media"):
            clean_src.pop(sub_key, None)
        clean_doc["source"] = clean_src
    elif isinstance(src, list):
        if src and isinstance(src[0], dict):
            clean_src = dict(src[0])
            for sub_key in ("content", "markdown_content", "raw_html", "raw", "authors", "prompt_used", "raw_source_file", "agent_provider", "media"):
                clean_src.pop(sub_key, None)
            clean_doc["source"] = clean_src

    return clean_doc


async def store_article():
    """Load articles from article_store into MongoDB if Mongo is connected."""
    if MongoHandle._db is None:
        return
    try:
        existing_docs = await MongoHandle.collection("articles").find({}, {"id": 1}).to_list(length=10000)
        existing_ids = {doc["id"] for doc in existing_docs if "id" in doc}

        articles = article_store.load_all_articles()
        if log:
            log.db("Syncing articles to MongoDB", f"{len(articles)} articles found")

        to_insert = [a for a in articles if isinstance(a, dict) and a.get("id") and a["id"] not in existing_ids]
        inserted = 0
        if to_insert:
            await MongoHandle.collection("articles").insert_many(to_insert)
            inserted = len(to_insert)
        if log:
            log.db("Sync complete", f"{inserted} new articles inserted")
    except Exception as e:
        if log:
            log.warn(f"MongoDB article sync skipped: {e}")


def start_scheduler():
    scheduler.add_job(store_article, IntervalTrigger(hours=24))
    scheduler.start()


def shutdown_scheduler():
    scheduler.shutdown()


async def _get_raw_articles() -> list[dict]:
    """Fetch candidate article pool from MongoDB (excluding heavy fields), falling back to article_store."""
    try:
        if MongoHandle._db is not None:
            cursor = MongoHandle.collection("articles").find(
                {},
                {
                    "content": 0, "markdown_content": 0, "summary": 0, "embedding": 0, "vector": 0,
                    "raw_html": 0, "raw": 0, "prompt_used": 0, "raw_source_file": 0,
                    "agent_provider": 0, "authors": 0, "media": 0, "source.content": 0,
                    "source.markdown_content": 0, "source.raw": 0, "source.authors": 0
                }
            ).limit(500)
            raw = await cursor.to_list(length=500)
            if raw:
                for doc in raw:
                    doc["_id"] = str(doc.get("_id", ""))
                cleaned = [_strip_heavy_fields(doc) for doc in raw]
                cleaned.sort(key=get_publication_timestamp, reverse=True)
                return cleaned
    except Exception as e:
        if log:
            log.warn(f"MongoDB article fetch failed ({e}). Falling back to ArticleStore.")

    # Fallback to ArticleStore (Azure Blob Store or FileStore)
    raw = article_store.load_all_articles()
    cleaned = [_strip_heavy_fields(art) if isinstance(art, dict) else art for art in raw]
    cleaned.sort(key=get_publication_timestamp, reverse=True)
    return cleaned


async def get_all_articles(current_user: dict):
    """
    Return top 20 articles in decreasing order of publication time, personalized if user is logged in.
    Uses Redis cache for unauthenticated default feeds.
    """
    user_doc = None
    if current_user and MongoHandle._db is not None:
        try:
            user_doc = await MongoHandle.collection("SNAPUsers").find_one({"email": current_user.get("email")})
        except Exception:
            pass

    # Check Redis cache for default unauthenticated feed
    if not user_doc:
        try:
            cached_feed = await RedisHandle.client().get("cache:feed:default")
            if cached_feed:
                return json.loads(cached_feed)
        except Exception:
            pass

    raw_articles = await _get_raw_articles()
    clean_articles = [_strip_heavy_fields(a) if isinstance(a, dict) else a for a in raw_articles]

    if not user_doc:
        sorted_by_date = sorted(clean_articles, key=get_publication_timestamp, reverse=True)
        res = {"feeds": sorted_by_date[:20]}
        try:
            await RedisHandle.client().set("cache:feed:default", json.dumps(res), ex=300)
        except Exception:
            pass
        return res

    preferences = user_doc.get("preferences", [])
    raw_weights = user_doc.get("bias", {})
    interactions = user_doc.get("category_scores", {cat: (0, 0.0) for cat in preferences})

    personalized = sort_articles(preferences, raw_weights, interactions, clean_articles)
    top20 = personalized[:20]
    return {"feeds": top20}


async def get_article_by_id(article_id: str, current_user: dict):
    """
    Fetch complete article details (including full text content) for single article view.
    Uses Redis cache with a 10-minute TTL.
    """
    # 1. Try Redis cache first
    cache_key = f"cache:article:detail:{article_id}"
    try:
        cached_article = await RedisHandle.client().get(cache_key)
        if cached_article:
            return json.loads(cached_article)
    except Exception:
        pass

    # 2. Fetch full article from MongoDB or fallback to ArticleStore
    article = None
    if MongoHandle._db is not None:
        try:
            article = await MongoHandle.collection("articles").find_one({"id": article_id})
        except Exception:
            pass

    if not article:
        article = article_store.load_article(article_id)

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if MongoHandle._db is not None:
        try:
            await MongoHandle.collection("articles").update_one({"id": article_id}, {"$inc": {"popularity": 1}})
        except Exception:
            pass

    article["popularity"] = article.get("popularity", 0) + 1
    if "_id" in article:
        article["_id"] = str(article["_id"])
    else:
        article["_id"] = article_id

    # Omit vector/embedding arrays and internal scraping metadata from detail response
    for internal_key in ("embedding", "vector", "prompt_used", "raw_source_file", "raw_html", "raw", "agent_provider"):
        article.pop(internal_key, None)

    # Clean nested source object in single article detail view
    src = article.get("source")
    if isinstance(src, dict):
        clean_src = dict(src)
        for sub_key in ("content", "markdown_content", "raw_html", "raw", "authors", "prompt_used", "raw_source_file", "agent_provider", "media"):
            clean_src.pop(sub_key, None)
        article["source"] = clean_src

    # 3. Store in Redis cache (10 min TTL)
    try:
        await RedisHandle.client().set(cache_key, json.dumps(article), ex=600)
    except Exception:
        pass

    return article


async def update_article_duration(article_id: str, duration: DurationRequest, current_user: dict):
    article = await get_article_by_id(article_id, current_user)
    added_seconds = duration.durationMs / 1000
    new_duration = article.get("duration", 0) + added_seconds

    if MongoHandle._db is not None:
        try:
            await MongoHandle.collection("articles").update_one(
                {"id": article_id},
                {"$set": {"duration": new_duration}}
            )
        except Exception:
            pass

    # Invalidate Redis detail cache so duration updates reflect
    try:
        await RedisHandle.client().delete(f"cache:article:detail:{article_id}")
    except Exception:
        pass

    if current_user and MongoHandle._db is not None:
        try:
            user_id = current_user.get("email")
            cat = article.get("category")
            user_doc = await MongoHandle.collection("SNAPUsers").find_one({"email": user_id})
            if user_doc:
                raw_weights = user_doc.get("bias", {})
                inter = user_doc.get("category_scores", {})

                new_weights = update_weights(raw_weights, inter, cat, clicked=True, duration=added_seconds)

                if log:
                    log.db("Updated user scores", str({k: f"{v:.3f}" for k, v in new_weights.items()}))
                await MongoHandle.collection("SNAPUsers").update_one(
                    {"email": user_id},
                    {"$set": {"bias": new_weights, "category_scores": inter}}
                )
        except Exception:
            pass

    return {
        "message": "Duration updated",
        "article_id": article_id,
        "added_duration_ms": duration.durationMs,
        "duration": new_duration
    }


async def get_all_articles_pagination(
    current_user: dict,
    page: int,
    limit: int,
) -> PaginatedArticlesResponse:
    skip = (page - 1) * limit

    # 1) Fetch candidate pool of documents (from Mongo if available, else from article_store)
    raw = await _get_raw_articles()
    clean: list[dict] = []
    for doc in raw:
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        else:
            doc["_id"] = str(doc.get("id", ""))
        doc.setdefault("markdown_content", None)
        doc.setdefault("location", None)

        src = doc.get("source", {})
        if isinstance(src, list):
            src = src[0] if src else {}

        content = src.get("content")
        if isinstance(content, list):
            src["content"] = " ".join(str(x) for x in content)

        media = src.get("media")
        if not isinstance(media, list):
            src["media"] = []

        doc["source"] = src
        clean.append(doc)

    # 2) Personalize & rank entire article pool
    user = None
    if current_user and MongoHandle._db is not None:
        try:
            user = await MongoHandle.collection("SNAPUsers").find_one({"email": current_user["email"]})
        except Exception:
            pass

    if user:
        prefs = user.get("preferences", [])
        weights = user.get("bias", {})
        interactions = user.get("category_scores", {c: (0, 0.0) for c in prefs})
        sorted_list = sort_articles(prefs, weights, interactions, clean)
    else:
        sorted_list = sorted(clean, key=get_publication_timestamp, reverse=True)

    # 3) Slice for requested page
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


# For testing
if __name__ == '__main__':
    import asyncio
    asyncio.run(store_article())
