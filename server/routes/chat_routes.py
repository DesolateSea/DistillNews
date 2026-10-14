from fastapi import APIRouter, Depends
from server.services.chat_service import get_chat, get_chat_without_article
from server.models.articles_model import ChatMessage
from server.auth import get_current_user
from server.limits import limit_user

router = APIRouter()


@router.post("/chat/{article_id}")
async def response_chat(article_id: str, payload: ChatMessage, current_user=Depends(get_current_user)):
    await limit_user(current_user, "chat", 20, 60)
    response = await get_chat(payload.message, article_id, current_user)
    return {"response": response}


@router.post("/chat")
async def response_chat_without_article(payload: ChatMessage, current_user=Depends(get_current_user)):
    await limit_user(current_user, "chat", 20, 60)
    response = await get_chat_without_article(payload.message, current_user)
    return {"response": response}
