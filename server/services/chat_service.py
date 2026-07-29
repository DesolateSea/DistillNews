import secrets
from typing import Optional
from service.articles import get_article_by_id


async def get_chat(message: str, article_id: str, current_user: Optional[dict] = None):
    from service.chatbot.wiring import get_chatbot_response
    from fastapi import HTTPException
    from service.db.mongo import MongoHandle

    try:
        data = await get_article_by_id(article_id)
    except Exception:
        data = None

    if not data:
        raise HTTPException(status_code=404, detail=f"Article with id '{article_id}' not found")

    title = data.get("title", "")
    category = data.get("category", "")
    summary = data.get("summary", "")
    content = data.get("content") or data.get("markdown_content") or summary

    article_text = (
        f"Title: {title}\n"
        f"Category: {category}\n"
        f"Summary: {summary}\n\n"
        f"Article Content:\n{content}"
    )

    user_doc = None
    if current_user and MongoHandle._db is not None:
        try:
            user_doc = await MongoHandle.collection("SNAPUsers").find_one({"email": current_user.get("email")})
        except Exception:
            pass

    user_id = str(user_doc["_id"]) if user_doc and "_id" in user_doc else secrets.token_hex(32)
    return get_chatbot_response(query=message, user_id=user_id, reading=article_text)


async def get_chat_without_article(message: str, current_user: Optional[dict] = None):
    from service.chatbot.wiring import get_chatbot_response
    from service.db.mongo import MongoHandle

    user_doc = None
    if current_user and MongoHandle._db is not None:
        try:
            user_doc = await MongoHandle.collection("SNAPUsers").find_one({"email": current_user.get("email")})
        except Exception:
            pass

    user_id = str(user_doc["_id"]) if user_doc and "_id" in user_doc else secrets.token_hex(32)
    return get_chatbot_response(query=message, user_id=user_id, reading=None)