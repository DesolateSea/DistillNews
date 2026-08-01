"""Chatbot orchestration with dual-mode context: autonomous global search vs. article-focused grounding."""

from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from service.agents.base import ToolCallingProvider, ToolDefinition, AgentMessage
from service.agents.orchestrator import AgentOrchestrator
from service.rag.base import DocumentStore

# Tool schema for news_search
NEWS_SEARCH_TOOL = ToolDefinition(
    name="news_search",
    description=(
        "Search the DistillNews article corpus for relevant news articles. "
        "Use this to find factual, grounded information when answering user questions about news, events, or current affairs. "
        "You decide the search keywords and how many results to retrieve."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keywords or phrase to find relevant articles."},
            "limit": {"type": "integer", "description": "Maximum number of articles to return (1-10).", "default": 5},
        },
        "required": ["query"],
    },
)

GET_ARTICLE_TOOL = ToolDefinition(
    name="get_article",
    description=(
        "Retrieve the full content of a specific article by its ID. "
        "Use this when a search result snippet is insufficient and you need the complete article text."
    ),
    parameters={
        "type": "object",
        "properties": {
            "article_id": {"type": "string", "description": "The unique article identifier."},
        },
        "required": ["article_id"],
    },
)

GLOBAL_SYSTEM_PROMPT = """You are DistillNews AI, a knowledgeable and friendly news assistant.

Your role is to help users stay informed by answering questions about news and current events.
You have access to a curated corpus of news articles through the `news_search` tool.

Guidelines:
- Use `news_search` to find relevant articles when answering factual questions about news, events, or current affairs.
- You decide the best search keywords and how many results to retrieve.
- If a search snippet is insufficient, use `get_article` to read the full article.
- Synthesize information from multiple sources when appropriate.
- Be concise (under 150 words) unless the user asks for detail.
- If no relevant articles are found, say so honestly rather than fabricating information.
- Use a conversational, engaging tone — like a knowledgeable friend sharing updates.
- End with a brief closing that invites further questions.
"""

ARTICLE_SYSTEM_PROMPT = """You are DistillNews AI, a knowledgeable and friendly news assistant.

The user is currently reading the article below. Answer their questions about it directly.
You have the `news_search` tool available if the user asks about related or comparative news topics.

Guidelines:
- Answer questions about the active article immediately using the context provided — no tool call needed.
- Use `news_search` only if the user asks about external or related news topics.
- Be concise (under 150 words) unless the user asks for detail.
- Use a conversational, engaging tone.

ACTIVE ARTICLE:
{article_context}
"""

class ChatbotService:
    """Dual-mode chatbot: autonomous tool-calling for global queries, article-grounded for reader sessions."""

    def __init__(
        self,
        agent: ToolCallingProvider,
        document_store: DocumentStore,
        prompts_dir: Path | None = None,
        logger: Any | None = None,
    ):
        self._agent = agent
        self._document_store = document_store
        self._logger = logger
        self._user_memory: dict[str, deque] = defaultdict(lambda: deque(maxlen=6))

        # Build tool executors
        self._tools = {
            "news_search": (NEWS_SEARCH_TOOL, self._execute_news_search),
            "get_article": (GET_ARTICLE_TOOL, self._execute_get_article),
        }
        self._orchestrator = AgentOrchestrator(
            agent=agent, tools=self._tools, max_turns=5
        )

    def get_response(
        self,
        query: str,
        user_id: str = "debug",
        reading: str | None = None,
        prompt: str = "chatbot.yaml",  # kept for API compat, ignored in new path
    ) -> str | None:
        self._log("chat_query", user_id, query)
        memory = self._user_memory[user_id]

        # Build system prompt based on mode
        if reading:
            system_prompt = ARTICLE_SYSTEM_PROMPT.format(article_context=reading)
        else:
            system_prompt = GLOBAL_SYSTEM_PROMPT

        # Append conversation memory
        if memory:
            system_prompt += "\n\nRecent conversation history:\n" + "\n".join(memory)

        self._log("ai_call", "chatbot_response", query)
        response = self._orchestrator.run(
            user_prompt=query, system_prompt=system_prompt
        )
        self._log("chat_response", response)

        memory.append(f"User: {query}")
        memory.append(f"Assistant: {response}")
        return response

    def _execute_news_search(self, query: str, limit: int = 5) -> list[dict]:
        self._log("rag_search", query, limit)
        results = self._document_store.search(query, limit=limit)
        return [
            {
                "id": r.metadata.get("id", ""),
                "title": r.title,
                "snippet": r.snippet or r.content[:300],
                "category": r.metadata.get("category", ""),
                "score": r.score,
            }
            for r in results
        ]

    def _execute_get_article(self, article_id: str) -> dict:
        from service.db import create_article_store
        store = create_article_store()
        article = store.load_article(article_id)
        if article is None:
            return {"error": f"Article '{article_id}' not found"}
        return {
            "title": article.get("title", ""),
            "content": article.get("content") or article.get("markdown_content") or article.get("summary", ""),
            "category": article.get("category", ""),
            "tags": article.get("tags", []),
        }

    def _log(self, method: str, *args: object) -> None:
        if self._logger:
            getattr(self._logger, method)(*args)
