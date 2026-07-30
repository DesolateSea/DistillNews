from fastapi import APIRouter, HTTPException, Depends
from server.auth import get_optional_user
from service.articles import get_all_articles, get_article_by_id, get_all_articles_pagination, search_articles
from server.models.articles_model import DurationRequest, PaginatedArticlesResponse
from server.utils.recommendation import update_weights
from service.db import MongoHandle

router = APIRouter()


async def _fetch_user_profile(current_user: dict | None) -> dict | None:
    if current_user and MongoHandle._db is not None:
        try:
            return await MongoHandle.collection("SNAPUsers").find_one({"email": current_user.get("email")})
        except Exception:
            pass
    return None


@router.get("/feeds")
async def feeds(category: str | None = None, current_user=Depends(get_optional_user)):
    user_profile = await _fetch_user_profile(current_user)
    return await get_all_articles_pagination(user_profile=user_profile, page=1, limit=20, category=category)


@router.get("/feeds/search")
async def search_feeds(q: str = "", category: str | None = None, page: int = 1, limit: int = 20):
    return await search_articles(query=q, category=category, page=page, limit=limit)


@router.get("/feeds/{article_id}")
async def article(article_id: str, current_user=Depends(get_optional_user)):
    return await get_article_by_id(article_id)


@router.post("/feeds/{article_id}/track_time")
async def track_time(article_id: str, duration: DurationRequest, current_user=Depends(get_optional_user)):
    article_data = await get_article_by_id(article_id)
    added_seconds = duration.durationMs / 1000
    new_duration = article_data.get("duration", 0) + added_seconds

    if current_user and MongoHandle._db is not None:
        try:
            user_id = current_user.get("email")
            cat = article_data.get("category")
            user_doc = await MongoHandle.collection("SNAPUsers").find_one({"email": user_id})
            if user_doc:
                raw_weights = user_doc.get("bias", {})
                inter = user_doc.get("category_scores", {})
                new_weights = update_weights(raw_weights, inter, cat, clicked=True, duration=added_seconds)
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


@router.get("/store_article")
async def store():
    return {"message": "ArticleStore active (MongoDB article sync disabled)"}


@router.get("/feeds/{page}/{limit}")
async def feeds_pagination(page: int, limit: int, category: str | None = None, current_user=Depends(get_optional_user)):
    user_profile = await _fetch_user_profile(current_user)
    return await get_all_articles_pagination(user_profile=user_profile, page=page, limit=limit, category=category)
