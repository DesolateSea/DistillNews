"""HuggingFace embedding-backed document store implementation."""

import json
import urllib.request
from config import config
from rag.base import Document, DocumentStore, SearchResult

try:
    from pipeline.logger import log
except ImportError:
    log = None


class HuggingFaceDocStore(DocumentStore):
    """Document store using HuggingFace feature extraction embeddings."""

    def __init__(
        self,
        api_key: str | None = None,
        embedding_model: str | None = None,
    ):
        self._api_key = api_key or config.HUGGINGFACE_API_KEY
        self._embedding_model = embedding_model or config.HUGGINGFACE_EMBEDDING_MODEL
        self._indexed_docs: list[dict] = []  # list of {"doc": Document, "embedding": list[float]}

    def _get_embedding(self, text: str) -> list[float]:
        url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self._embedding_model}"
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload = {"inputs": text.replace("\n", " ").strip() or " "}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                # Feature extraction returns nested array if token level, average to vector
                if isinstance(res, list) and res and isinstance(res[0], list):
                    # Mean pooling over tokens
                    dims = len(res[0])
                    mean_emb = [sum(token[i] for token in res) / len(res) for i in range(dims)]
                    return mean_emb
                elif isinstance(res, list) and all(isinstance(x, (int, float)) for x in res):
                    return res
                return []
        except Exception as error:
            if log:
                log.error(f"HF embedding error ({self._embedding_model})", str(error))
            return []

    def upload(self, documents: list[Document]) -> None:
        """Upload and compute embeddings for documents via HuggingFace."""
        if not documents:
            return

        if log:
            log.info(f"HF DocStore: Embedding {len(documents)} docs with '{self._embedding_model}'")

        for doc in documents:
            text = f"{doc.title}\n{doc.content}"
            emb = self._get_embedding(text)
            if emb:
                self._indexed_docs.append({"doc": doc, "embedding": emb})

        if log:
            log.success(f"HF DocStore: Indexed {len(self._indexed_docs)} documents total")

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
