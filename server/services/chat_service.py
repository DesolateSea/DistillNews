import secrets
from typing import Optional
from service.db import create_article_store

article_store = create_article_store()


async def get_chat(message: str, article_id: str, current_user=None):
    from service.chatbot.wiring import get_chatbot_response
    from fastapi import HTTPException
    from service.db.mongo import MongoHandle

    data = article_store.load_article(article_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Article with id '{article_id}' not found")

    article = data.get("content") or data.get("markdown_content") or data.get("summary") or ""
    if current_user is None:
        random_string = secrets.token_hex(32)
        return get_chatbot_response(query=message, user_id=random_string, reading=article)

    user_doc = None
    if MongoHandle._db is not None:
        try:
            user_doc = await MongoHandle.collection("SNAPUsers").find_one({"email": current_user.get("email")})
        except Exception:
            pass

    user_id = str(user_doc["_id"]) if user_doc and "_id" in user_doc else secrets.token_hex(32)
    return get_chatbot_response(query=message, user_id=user_id, reading=article)


async def get_chat_without_article(message: str, current_user=None):
    from service.chatbot.wiring import get_chatbot_response
    from service.db.mongo import MongoHandle

    if current_user is None:
        random_string = secrets.token_hex(32)
        return get_chatbot_response(query=message, user_id=random_string, reading=None)

    user_doc = None
    if MongoHandle._db is not None:
        try:
            user_doc = await MongoHandle.collection("SNAPUsers").find_one({"email": current_user.get("email")})
        except Exception:
            pass

    user_id = str(user_doc["_id"]) if user_doc and "_id" in user_doc else secrets.token_hex(32)
    return get_chatbot_response(query=message, user_id=user_id, reading=None)