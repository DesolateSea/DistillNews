from fastapi import APIRouter, Body, Depends, HTTPException
from typing import Optional, Union, Dict, Any
from server.services.chat_service import get_chat, get_chat_without_article
from server.models.articles_model import ChatMessage
from server.auth import get_optional_user

router = APIRouter()


@router.post("/chat/{article_id}")
async def response_chat(
    article_id: str,
    payload: Union[ChatMessage, Dict[str, Any], str] = Body(...),
    current_user: Optional[dict] = Depends(get_optional_user),
):
    if isinstance(payload, ChatMessage):
        message_text = payload.message
    elif isinstance(payload, dict):
        message_text = payload.get("message", "")
    else:
        message_text = str(payload)

    if not message_text:
        raise HTTPException(status_code=400, detail="Field 'message' is required")

    response_text = await get_chat(message=message_text, article_id=article_id, current_user=current_user)
    return {"response": response_text}


@router.post("/chat")
async def response_chat_without_article(
    payload: Union[ChatMessage, Dict[str, Any], str] = Body(...),
    current_user: Optional[dict] = Depends(get_optional_user),
):
    if isinstance(payload, ChatMessage):
        message_text = payload.message
    elif isinstance(payload, dict):
        message_text = payload.get("message", "")
    else:
        message_text = str(payload)

    if not message_text:
        raise HTTPException(status_code=400, detail="Field 'message' is required")

    response_text = await get_chat_without_article(message=message_text, current_user=current_user)
    return {"response": response_text}