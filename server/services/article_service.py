from fastapi import HTTPException
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from server.models.articles_model import DurationRequest, ArticleInDB, PaginatedArticlesResponse
from server.utils.recommendation import sort_articles, update_weights
from service.db import MongoHandle, create_article_store

try:
    from service.logger import log
except ImportError:
    log = None

scheduler = AsyncIOScheduler()
article_store = create_article_store()


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
    """Fetch candidate article pool from MongoDB if available, otherwise directly from article_store."""
    try:
        if MongoHandle._db is not None:
            cursor = MongoHandle.collection("articles").find().limit(500)
            raw = await cursor.to_list(length=500)
            if raw:
                for doc in raw:
                    doc["_id"] = str(doc.get("_id", ""))
                return raw
    except Exception as e:
        if log:
            log.warn(f"MongoDB article fetch failed ({e}). Falling back to ArticleStore.")

    # Fallback to ArticleStore (Azure Blob Store or FileStore)
    return article_store.load_all_articles()


async def get_all_articles(current_user: dict):
    """
    Return top 20 articles, personalized if user is logged in.
    Uses user's category_scores as weights for recommendation.
    """
    raw_articles = await _get_raw_articles()

    user_doc = None
    if current_user and MongoHandle._db is not None:
        try:
            user_doc = await MongoHandle.collection("SNAPUsers").find_one({"email": current_user.get("email")})
        except Exception:
            pass

    if not user_doc:
        sorted_by_pop = sorted(raw_articles, key=lambda a: a.get("popularity", 0), reverse=True)
        return {"feeds": sorted_by_pop[:20]}

    preferences = user_doc.get("preferences", [])
    raw_weights = user_doc.get("bias", {})
    interactions = user_doc.get("category_scores", {cat: (0, 0.0) for cat in preferences})

    personalized = sort_articles(preferences, raw_weights, interactions, raw_articles)
    top20 = personalized[:20]
    return {"feeds": top20}


async def get_article_by_id(article_id: str, current_user: dict):
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
        sorted_list = sorted(clean, key=lambda a: a.get("popularity", 0), reverse=True)

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
