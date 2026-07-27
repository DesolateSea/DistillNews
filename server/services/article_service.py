from fastapi import HTTPException
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from server.models.articles_model import DurationRequest, ArticleInDB, PaginatedArticlesResponse
from server.utils.recommendation import sort_articles, update_weights
from service.db import FileStore, MongoHandle

<<<<<<< HEAD:backend/server/services/article_service.py
from utils.logger import log
=======
try:
    from service.logger import log
except ImportError:
    log = None
>>>>>>> 582a92f (refactor: The code base has sperated the pipelines completely from the):server/services/article_service.py

scheduler = AsyncIOScheduler()


async def store_article():
    """Load articles from JSON files into MongoDB if not present."""
    files = FileStore.list_processed_files()
    if log:
        log.db("Syncing articles to MongoDB", f"{len(files)} JSON files found")
    inserted = 0
    for file in files:
        article = FileStore.read_json(file)
        if isinstance(article, dict):
            article["id"] = file.stem

            existing = await MongoHandle.collection("articles").find_one({"id": article["id"]})
            if not existing:
                await MongoHandle.collection("articles").insert_one(article)
                inserted += 1
    if log:
        log.db("Sync complete", f"{inserted} new articles inserted")


def start_scheduler():
    scheduler.add_job(store_article, IntervalTrigger(hours=24))
    scheduler.start()


def shutdown_scheduler():
    scheduler.shutdown()

async def get_all_articles(current_user: dict):
    """
    Return top 20 articles, personalized if user is logged in.
    Uses user's category_scores as weights for recommendation.
    """
    # Fetch raw articles
    
    cursor = MongoHandle.collection("articles").find().limit(50)
    raw_articles = await cursor.to_list(length=50)
    # Convert ObjectId->_id to string
    for doc in raw_articles:
        doc["_id"] = str(doc.get("_id"))

    # If no user or no category_scores, fallback to popularity sort
    if not current_user:
        sorted_by_pop = sorted(raw_articles, key=lambda a: a.get("popularity", 0), reverse=True)
        return {"feeds": sorted_by_pop[:20]}
    current_user = await MongoHandle.collection("SNAPUsers").find_one({"email":current_user.get("email")})

    # Extract user data
    preferences = current_user.get("preferences", [])
    raw_weights = current_user.get("bias", {})
    # Load interaction data, default empty
    interactions = current_user.get("category_scores", {cat: (0, 0.0) for cat in preferences})

    # Generate personalized ordering
    personalized = sort_articles(preferences, raw_weights, interactions, raw_articles)
    top20 = personalized[:20]
    return {"feeds": top20}

async def get_article_by_id(article_id: str, current_user: dict):
    article = await MongoHandle.collection("articles").find_one({"id": article_id})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Increment popularity in DB
    await MongoHandle.collection("articles").update_one({"id": article_id}, {"$inc": {"popularity": 1}})
    # Reflect increment locally
    article["popularity"] = article.get("popularity", 0) + 1
    article["_id"] = str(article.get("_id"))
    return article

async def update_article_duration(article_id: str, duration: DurationRequest, current_user: dict ):
    article = await MongoHandle.collection("articles").find_one({"id": article_id})
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    added_seconds = duration.durationMs / 1000
    new_duration = article.get("duration", 0) + added_seconds
    # Update in DB
    await MongoHandle.collection("articles").update_one(
        {"id": article_id},
        {"$set": {"duration": new_duration}}
    )
    # current_user logged for debugging
    # Optionally update user's interaction and weights
    if current_user:
        user_id = current_user.get("email")
        cat = article.get("category")
        # Fetch latest user doc
        user_doc = await MongoHandle.collection("SNAPUsers").find_one({"email": user_id})
        prefs = user_doc.get("preferences", [])
        raw_weights = user_doc.get("bias", {})
        # Normalize existing weights
        total_w = sum(raw_weights.values()) or 1.0
        weights = {c: raw_weights.get(c, 0) / total_w for c in prefs}
        inter = user_doc.get("category_scores", {c: (0,0.0) for c in prefs})
        # Update weights based on view
        new_weights = update_weights(weights, inter, cat, clicked=True, duration=added_seconds)
        # Save back
        # Denormalize weights back to category_scores scale
        updated_scores = {c: new_weights.get(c, 0) for c in prefs}
        if log:
            log.db("Updated user scores", str({k: f"{v:.3f}" for k, v in updated_scores.items()}))
        await MongoHandle.collection("SNAPUsers").update_one(
            {"email": user_id},
            {"$set": {"bias": new_weights, "category_scores": inter}}
        )

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

    # 1) Fetch one page of raw docs
    raw = await MongoHandle.collection("articles").find().skip(skip).limit(limit).to_list(length=limit)
    clean: list[dict] = []
    for doc in raw:
        # ——————————————————————————————————————————————
        # 1) _id must be a string
        doc["_id"] = str(doc["_id"])

        # 3) optional top‑level defaults
        doc.setdefault("markdown_content", None)
        doc.setdefault("location", None)

        # ——————————————————————————————————————————————
        # 4) clean nested source
        src = doc.get("source", {})

        #    a) if `source` is a list, take the first element
        if isinstance(src, list):
            src = src[0] if src else {}

        #    b) join list‑of‑strings in `content` into one string
        content = src.get("content")
        if isinstance(content, list):
            src["content"] = " ".join(str(x) for x in content)

        #    c) ensure `media` is always a list
        media = src.get("media")
        if not isinstance(media, list):
            src["media"] = []

        doc["source"] = src
        # ——————————————————————————————————————————————

        clean.append(doc)

    # 3) Sort / personalize
    if not current_user:
        sorted_list = sorted(clean, key=lambda a: a.get("popularity", 0), reverse=True)
    else:
        user = await MongoHandle.collection("SNAPUsers").find_one({"email": current_user["email"]})
        prefs = user.get("preferences", [])
        weights = user.get("bias", {})
        interactions = user.get("category_scores", {c: (0, 0.0) for c in prefs})
        sorted_list = sort_articles(prefs, weights, interactions, clean)

    # 4) Count & has_more
    total = await MongoHandle.collection("articles").count_documents({})
    has_more = (skip + len(sorted_list)) < total

    return {
        "page":page,
        "limit":limit,
        "has_more":has_more,
        "total":total,
        "feeds":sorted_list,
    }


# For testing
if __name__ == '__main__':
    import asyncio
    asyncio.run(store_article())
