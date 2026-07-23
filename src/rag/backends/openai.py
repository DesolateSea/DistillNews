"""OpenAI / Azure Foundry embedding-based document store implementation."""

import math
from config import config
from rag.base import Document, DocumentStore, SearchResult

try:
    from pipeline.logger import log
except ImportError:
    log = None


class OpenAIDocStore(DocumentStore):
    """Document store using OpenAI / Foundry embeddings and in-memory vector search."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        embedding_model: str | None = None,
    ):
        from openai import OpenAI

        self._api_key = api_key or config.OPENAI_API_KEY
        self._base_url = base_url or config.OPENAI_BASE_URL
        self._embedding_model = embedding_model or config.OPENAI_EMBEDDING_MODEL

        if not self._api_key:
            raise ValueError("An API key is required. Set FOUNDRY_API_KEY or OPENAI_API_KEY.")

        client_kwargs: dict = {"api_key": self._api_key}
        if self._base_url:
            client_kwargs["base_url"] = self._base_url

        self._client = OpenAI(**client_kwargs)
        self._indexed_docs: list[dict] = []  # list of {"doc": Document, "embedding": list[float]}

    def _get_embedding(self, text: str) -> list[float]:
        text_clean = text.replace("\n", " ").strip()
        if not text_clean:
            return []
        response = self._client.embeddings.create(
            model=self._embedding_model,
            input=text_clean,
        )
        return response.data[0].embedding

    def _get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        cleaned = [t.replace("\n", " ").strip() or " " for t in texts]
        response = self._client.embeddings.create(
            model=self._embedding_model,
            input=cleaned,
        )
        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]

    def upload(self, documents: list[Document]) -> None:
        """Upload and compute embeddings for a batch of documents."""
        if not documents:
            return

        if log:
            log.info(f"OpenAI DocStore: Embedding {len(documents)} docs with model '{self._embedding_model}'")

        batch_size = 50
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i : i + batch_size]
            texts = [f"{doc.title}\n{doc.content}" for doc in batch_docs]
            try:
                embeddings = self._get_embeddings_batch(texts)
                for doc, emb in zip(batch_docs, embeddings):
                    self._indexed_docs.append({"doc": doc, "embedding": emb})
            except Exception as e:
                if log:
                    log.error("Embedding batch upload failed", str(e))

        if log:
            log.success(f"OpenAI DocStore: Indexed {len(self._indexed_docs)} documents total")

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        """Search indexed documents by vector similarity."""
        if not query or not self._indexed_docs:
            return []

        try:
            query_emb = self._get_embedding(query)
        except Exception as e:
            if log:
                log.error("Failed to generate query embedding", str(e))
            return []

        if not query_emb:
            return []

        scores = []
        for item in self._indexed_docs:
            doc_emb = item["embedding"]
            # Cosine similarity (dot product for normalized embeddings)
            dot = sum(q * d for q, d in zip(query_emb, doc_emb))
            scores.append((dot, item["doc"]))

        scores.sort(key=lambda x: x[0], reverse=True)
        top_results = scores[:limit]

        results = []
        for score, doc in top_results:
            snippet = doc.content[:300] + "..." if len(doc.content) > 300 else doc.content
            results.append(
                SearchResult(
                    title=doc.title,
                    content=doc.content,
                    snippet=snippet,
                    score=float(score),
                )
            )

        return results
