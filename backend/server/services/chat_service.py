from db.mongo import MongoHandle
import os
import secrets
from typing import Optional

async def get_chat(message: str, article_id: str, current_user=None):
    from chatbot.wiring import get_chatbot_response
    from fastapi import HTTPException

    data = await MongoHandle.collection("articles").find_one({"id": article_id})
    if not data:
        raise HTTPException(status_code=404, detail=f"Article with id '{article_id}' not found")

    article = data.get("content", "")
    if current_user is None:
        random_string = secrets.token_hex(32)
        return get_chatbot_response(query=message, user_id=random_string, reading=article)
    user_doc = await MongoHandle.collection("SNAPUsers").find_one({"email": current_user["email"]})
    user_id = user_doc["_id"] if user_doc else secrets.token_hex(32)
    return get_chatbot_response(query=message, user_id=user_id, reading=article)

async def get_chat_without_article(message: str, current_user=None):
    from chatbot.wiring import get_chatbot_response

    if current_user is None:
        random_string = secrets.token_hex(32)
        return get_chatbot_response(query=message, user_id=random_string, reading=None)
    user_id = await MongoHandle.collection("SNAPUsers").find_one({"email": current_user["email"]})
    user_id = user_id["_id"]
    return get_chatbot_response(query=message, user_id=user_id, reading=None)