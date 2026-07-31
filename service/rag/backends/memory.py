"""Provider-agnostic, in-process semantic document store."""

import math
import re
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
                    else:
                        self._indexed_docs.append({"doc": document, "embedding": []})
            except Exception as error:
                if log:
                    log.error("Document embedding failed", str(error))
                for document in docs_to_embed:
                    self._indexed_docs.append({"doc": document, "embedding": []})

        if log:
            log.success(f"Vector store: Indexed {len(self._indexed_docs)} documents total")

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        """Return the nearest documents by cosine similarity, falling back to lexical matching."""
        if not query or limit <= 0 or not self._indexed_docs:
            if log:
                log.warn("RAG Search aborted", f"Empty query or 0 indexed docs (total indexed: {len(self._indexed_docs)})")
            return []

        query_embedding = []
        if self._embedder:
            try:
                query_embedding = self._embedder.embed(query)
            except Exception as error:
                if log:
                    log.error("Query embedding failed", str(error))

        scored_documents = []

        if query_embedding:
            if log:
                log.info("RAG Search Mode: Vector Cosine Similarity", f"Query vector dims: {len(query_embedding)}")
            try:
                import numpy as np
                valid_docs = []
                doc_vectors = []
                dim = len(query_embedding)
                for item in self._indexed_docs:
                    emb = item.get("embedding")
                    if emb and len(emb) == dim:
                        doc_vectors.append(emb)
                        valid_docs.append(item["doc"])

                if doc_vectors:
                    matrix = np.array(doc_vectors, dtype=np.float32)
                    q_vec = np.array(query_embedding, dtype=np.float32)

                    matrix_norms = np.linalg.norm(matrix, axis=1)
                    q_norm = np.linalg.norm(q_vec)

                    matrix_norms[matrix_norms == 0] = 1e-10
                    q_norm = 1e-10 if q_norm == 0 else q_norm

                    similarities = np.dot(matrix, q_vec) / (matrix_norms * q_norm)
                    for sim, doc in zip(similarities, valid_docs):
                        if sim > 0:
                            scored_documents.append((float(sim), doc))
                    scored_documents.sort(key=lambda item: item[0], reverse=True)
            except ImportError:
                for item in self._indexed_docs:
                    doc_emb = item.get("embedding")
                    if doc_emb and len(doc_emb) == len(query_embedding):
                        sim = self._cosine_similarity(query_embedding, doc_emb)
                        if sim > 0:
                            scored_documents.append((sim, item["doc"]))
                scored_documents.sort(key=lambda item: item[0], reverse=True)
        else:
            query_terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
            if log:
                log.info("RAG Search Mode: Lexical Keyword Fallback", f"Search terms: {query_terms}")
            if not query_terms:
                return []
            
            for item in self._indexed_docs:
                doc = item["doc"]
                text = f"{doc.title} {doc.content}".lower()
                matches = sum(text.count(term) for term in query_terms)
                if matches > 0:
                    score = min(1.0, matches / (len(query_terms) * 2.0))
                    scored_documents.append((score, doc))
            scored_documents.sort(key=lambda item: item[0], reverse=True)

        results = [
            SearchResult(
                title=document.title,
                content=document.content,
                snippet=self._snippet(document.content),
                score=round(score, 4),
                metadata=document.metadata or {},
            )
            for score, document in scored_documents[:limit]
        ]

        if log:
            if results:
                log.success(f"RAG Search Found {len(results)} matches", f"Top match: '{results[0].title[:45]}' (score: {results[0].score})")
            else:
                log.warn("RAG Search → 0 results found", f"Searched {len(self._indexed_docs)} documents for: '{query[:50]}'")

        return results

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
