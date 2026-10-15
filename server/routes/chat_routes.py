from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from server.services.chat_service import get_chat, get_chat_without_article
from server.models.articles_model import ChatMessage
from server.auth import get_optional_user
from server.limits import limit_key, limit_user

router = APIRouter()


async def chat_identity(request: Request, current_user=Depends(get_optional_user)):
    if current_user is not None:
        await limit_user(current_user, "chat", 20, 60)
        return current_user
    # Do not trust forwarded headers or share history among guests behind a proxy.
    peer = request.client.host if request.client else "unknown"
    await limit_key(peer, "guest:chat", 20, 60)
    return {"_id": f"guest:{uuid4().hex}"}


@router.post("/chat/{article_id}")
async def response_chat(article_id: str, payload: ChatMessage, current_user=Depends(chat_identity)):
    response = await get_chat(payload.message, article_id, current_user)
    return {"response": response}


@router.post("/chat")
async def response_chat_without_article(payload: ChatMessage, current_user=Depends(chat_identity)):
    response = await get_chat_without_article(payload.message, current_user)
    return {"response": response}
