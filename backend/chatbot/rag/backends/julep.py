"""
Julep document store backend.

Uses the Julep SDK's built-in document storage and search API.
"""

import os
from config import config
from chatbot.rag.base import DocumentStore, Document, SearchResult


class JulepDocStore(DocumentStore):
    """DocumentStore backed by Julep's agent document API.

    Creates a dedicated Julep agent for document storage.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        environment: str | None = None,
        agent_name: str = "RAG Doc Store",
    ):
        from julep import Julep, ConflictError  # defer import

        self._ConflictError = ConflictError

        self._client = Julep(
            api_key=api_key or config.JULEP_API_KEY,
            environment=environment or config.JULEP_ENVIRONMENT,
        )

        _model = model or config.JULEP_MODEL

        # Create a dedicated agent for doc storage
        self._agent = self._client.agents.create(
            name=agent_name,
            model=_model,
            about="Agent used for document storage and retrieval.",
        )

    # ------------------------------------------------------------------
    # DocumentStore interface
    # ------------------------------------------------------------------

    def upload(self, documents: list[Document]) -> None:
        """Upload documents to Julep's agent doc store."""
        for doc in documents:
            try:
                self._client.agents.docs.create(
                    agent_id=self._agent.id,
                    title=doc.title,
                    content=doc.content,
                    metadata=doc.metadata or {},
                )
            except self._ConflictError:
                # Document already exists — skip
                continue

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        """Search Julep's agent doc store."""
        results = self._client.agents.docs.search(
            agent_id=self._agent.id,
            text=query,
            limit=limit,
        )

        results_dict = results.model_dump()
        docs = results_dict.get("docs", [])

        return [
            SearchResult(
                title=doc.get("title", "Unknown"),
                content=doc.get("content", ""),
                snippet=doc.get("snippet", {}).get("content", ""),
                score=doc.get("score"),
                metadata=doc.get("metadata") or {},
            )
            for doc in docs
        ]
