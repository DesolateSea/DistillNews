"""Chatbot orchestration over abstract chat and retrieval interfaces."""

from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from agents.base import AgentProvider
from chatbot.rag.base import DocumentStore


class ChatbotService:
    """Generate grounded responses without knowing pipeline or embedding details.

    The service only asks a ``DocumentStore`` for results. Whether that store
    uses local Ollama vectors, an OpenAI-compatible endpoint, or no embeddings
    at all is determined outside the chatbot.
    """

    def __init__(
        self,
        agent: AgentProvider,
        document_store: DocumentStore,
        prompts_dir: Path,
        logger: Any | None = None,
    ):
        self._agent = agent
        self._document_store = document_store
        self._prompts_dir = prompts_dir
        self._logger = logger
        self._user_memory = defaultdict(lambda: deque(maxlen=6))

    def get_response(
        self,
        query: str,
        user_id: str = "debug",
        reading: str | None = None,
        prompt: str = "chatbot.yaml",
    ) -> str | None:
        """Generate a response grounded in the configured document store."""
        self._log("chat_query", user_id, query)
        memory = self._user_memory[user_id]

        filtered = self._filter_prompt(query)
        search_results = self._document_store.search(filtered, limit=5)
        self._log("rag_search", filtered, len(search_results))

        if not search_results:
            context = "No relevant articles found."
            self._log("warn", "No RAG results for query")
        else:
            context = "\n\n".join(
                result.snippet or result.content for result in search_results
            )

        self._log("ai_call", "chatbot_response", query)
        result = self._agent.complete_from_template(
            self._prompts_dir / prompt,
            {
                "query": query,
                "reading": reading or "",
                "content": context,
                "memory": "\n".join(memory),
            },
        )
        response = result.content
        self._log("chat_response", response)

        memory.append(f"User: {query}")
        memory.append(f"Assistant: {response}")
        return response

    def _filter_prompt(self, query: str) -> str:
        self._log("ai_call", "keyword_extraction", query)
        result = self._agent.complete_from_template(
            self._prompts_dir / "filter_prompt.yaml", {"query": query}
        )
        self._log("ai_result", "keyword_extraction", result.content)
        return result.content

    def _log(self, method: str, *args: object) -> None:
        if self._logger:
            getattr(self._logger, method)(*args)
