import asyncio
import logging
from typing import Optional
from service.articles import get_article_by_id
from fastapi import HTTPException

_jobs = set()
_users = set()


async def run_chat(message, user, reading):
    identity = str(user["_id"])
    if len(_jobs) >= 2 or identity in _users:
        raise HTTPException(503, "Chat busy; try again later")
    _users.add(identity)
    def work():
        from service.chatbot.wiring import get_chatbot_response
        return get_chatbot_response(query=message, user_id=identity, reading=reading)
    task = asyncio.create_task(asyncio.to_thread(work))
    _jobs.add(task)

    def finished(job):
        _jobs.discard(job)
        _users.discard(identity)
        if not job.cancelled():
            job.exception()
    task.add_done_callback(finished)
    try:
        return await asyncio.wait_for(asyncio.shield(task), timeout=60)
    except TimeoutError:
        raise HTTPException(504, "Chat timed out")
    except Exception as error:
        # Avoid logging provider bodies, prompts, credentials or user messages.
        logging.getLogger(__name__).error(
            "Chat worker failed: type=%s status=%s code=%s",
            type(error).__name__, getattr(error, "status_code", None),
            getattr(error, "code", None),
        )
        raise HTTPException(502, "Chat provider unavailable")


async def get_chat(message: str, article_id: str, current_user: Optional[dict] = None):
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

    return await run_chat(message, current_user, article_text[:16000])


async def get_chat_without_article(message: str, current_user: Optional[dict] = None):
    return await run_chat(message, current_user, None)
