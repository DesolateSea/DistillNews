"""Provider-agnostic, in-process semantic document store."""

import math

from service.rag.base import Document, DocumentStore, SearchResult, EmbeddingProvider

try:
    from service.logger import log
except ImportError:
    log = None


class InMemoryVectorStore(DocumentStore):
    """Index documents locally using vectors from an ``EmbeddingProvider``.

    The store has no knowledge of whether vectors are created by a local or
    remote provider.
    """

    def __init__(self, embedder: EmbeddingProvider):
        self._embedder = embedder
        self._indexed_docs: list[dict] = []

    def upload(self, documents: list[Document]) -> None:
        """Retain documents and reuse pre-computed vectors or generate new ones."""
        if not documents:
            return

        if log:
            log.info(f"Vector store: Indexing {len(documents)} documents")

        docs_to_embed = []
        for document in documents:
            pre_emb = document.metadata.get("embedding") if document.metadata else None
            if pre_emb and isinstance(pre_emb, list) and len(pre_emb) > 0:
                self._indexed_docs.append({"doc": document, "embedding": pre_emb})
            else:
                docs_to_embed.append(document)

        if docs_to_embed and self._embedder:
            texts = [f"{document.title}\n{document.content}" for document in docs_to_embed]
            try:
                embeddings = self._embedder.embed_many(texts)
                for document, embedding in zip(docs_to_embed, embeddings):
                    if embedding:
                        self._indexed_docs.append({"doc": document, "embedding": embedding})
            except Exception as error:
                if log:
                    log.error("Document embedding failed", str(error))

        if log:
            log.success(f"Vector store: Indexed {len(self._indexed_docs)} documents total")

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        """Return the nearest documents by cosine similarity."""
        if not query or limit <= 0 or not self._indexed_docs:
            return []

        try:
            query_embedding = self._embedder.embed(query)
        except Exception as error:
            if log:
                log.error("Query embedding failed", str(error))
            return []
        if not query_embedding:
            return []

        scored_documents = [
            (self._cosine_similarity(query_embedding, item["embedding"]), item["doc"])
            for item in self._indexed_docs
        ]
        scored_documents.sort(key=lambda item: item[0], reverse=True)

        return [
            SearchResult(
                title=document.title,
                content=document.content,
                snippet=self._snippet(document.content),
                score=score,
                metadata=document.metadata or {},
            )
            for score, document in scored_documents[:limit]
        ]

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        """Compare vectors safely, including providers with different dimensions."""
        if len(left) != len(right):
            return 0.0
        pairs = list(zip(left, right))
        if not pairs:
            return 0.0
        dot_product = sum(a * b for a, b in pairs)
        left_magnitude = math.sqrt(sum(a * a for a, _ in pairs))
        right_magnitude = math.sqrt(sum(b * b for _, b in pairs))
        if not left_magnitude or not right_magnitude:
            return 0.0
        return float(dot_product / (left_magnitude * right_magnitude))

    @staticmethod
    def _snippet(content: str, length: int = 300) -> str:
        return f"{content[:length]}..." if len(content) > length else content
