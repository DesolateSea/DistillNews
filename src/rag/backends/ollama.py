"""Ollama local embedding-backed document store implementation."""

import json
import urllib.request
from config import config
from rag.base import Document, DocumentStore, SearchResult

try:
    from pipeline.logger import log
except ImportError:
    log = None


class OllamaDocStore(DocumentStore):
    """Document store using local Ollama embeddings and vector search."""

    def __init__(
        self,
        base_url: str | None = None,
        embedding_model: str | None = None,
    ):
        self._base_url = (base_url or config.OLLAMA_BASE_URL).rstrip("/")
        self._embedding_model = embedding_model or config.OLLAMA_EMBEDDING_MODEL
        self._indexed_docs: list[dict] = []  # list of {"doc": Document, "embedding": list[float]}

    def _get_embedding(self, text: str) -> list[float]:
        url = f"{self._base_url}/api/embeddings"
        payload = {
            "model": self._embedding_model,
            "prompt": text.replace("\n", " ").strip() or " ",
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("embedding", [])
        except Exception as error:
            if log:
                log.error(f"Ollama embedding error ({self._embedding_model})", str(error))
            return []

    def upload(self, documents: list[Document]) -> None:
        """Upload and compute embeddings for documents via local Ollama."""
        if not documents:
            return

        if log:
            log.info(f"Ollama DocStore: Embedding {len(documents)} docs with '{self._embedding_model}'")

        for doc in documents:
            text = f"{doc.title}\n{doc.content}"
            emb = self._get_embedding(text)
            if emb:
                self._indexed_docs.append({"doc": doc, "embedding": emb})

        if log:
            log.success(f"Ollama DocStore: Indexed {len(self._indexed_docs)} documents total")

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        """Search indexed documents by vector similarity."""
        if not query or not self._indexed_docs:
            return []

        query_emb = self._get_embedding(query)
        if not query_emb:
            return []

        scores = []
        for item in self._indexed_docs:
            doc_emb = item["embedding"]
            # Dot product (or cosine similarity)
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
