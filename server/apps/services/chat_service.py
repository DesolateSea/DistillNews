import sys
import os
import secrets
from typing import Optional
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../src')))
from fastapi import APIRouter
from apps.core.config import DB_URL
from motor.motor_asyncio import AsyncIOMotorClient
router = APIRouter()
client = AsyncIOMotorClient(DB_URL)
articles_collection = client.news_db.articles
users_collection = client.news_db.SNAPUsers

async def get_chat(message: str, article_id: str, current_user=None):
    from pipeline.chatbot import get_chatbot_response
    from fastapi import HTTPException

    data = await articles_collection.find_one({"id": article_id})
    if not data:
        raise HTTPException(status_code=404, detail=f"Article with id '{article_id}' not found")

    article = data.get("content", "")
    if current_user is None:
        random_string = secrets.token_hex(32)
        return get_chatbot_response(query=message, user_id=random_string, reading=article)
    user_doc = await users_collection.find_one({"email": current_user["email"]})
    user_id = user_doc["_id"] if user_doc else secrets.token_hex(32)
    return get_chatbot_response(query=message, user_id=user_id, reading=article)

async def get_chat_without_article(message: str, current_user=None):
    from pipeline.chatbot import get_chatbot_response

    if current_user is None:
        random_string = secrets.token_hex(32)
        return get_chatbot_response(query=message, user_id=random_string, reading=None)
    user_id = await users_collection.find_one({"email": current_user["email"]})
    user_id = user_id["_id"]
    return get_chatbot_response(query=message, user_id=user_id, reading=None)