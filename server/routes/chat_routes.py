from fastapi import APIRouter, Body
from server.services.chat_service import get_chat,get_chat_without_article
from server.models.articles_model import ChatMessage
from server.auth import get_optional_user
from fastapi import Depends
from typing import Optional
router = APIRouter()

@router.post("/chat/{article_id}")
async def response_chat(message: str, article_id: str, current_user: Optional[dict]=None):
    return await get_chat(message=message, article_id=article_id)

@router.post("/chat")
async def response_chat_without_article(message = Body(...)):
    return {"response": await get_chat_without_article(message=message)}