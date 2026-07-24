"""Pure Python Okapi BM25 document store for zero-cost lexical retrieval."""

import math
import re
from chatbot.rag.base import Document, DocumentStore, SearchResult

try:
    from pipeline.logger import log
except ImportError:
    log = None


class BM25DocStore(DocumentStore):
    """Rank documents using Okapi BM25 algorithm.

    Requires zero LLM calls, zero embedding models, and zero external APIs.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._documents: list[Document] = []
        self._doc_tokens: list[list[str]] = []
        self._doc_lengths: list[int] = []
        self._avg_doc_len: float = 0.0
        self._doc_frequencies: dict[str, int] = {}

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Convert text into lowercase word tokens."""
        return re.findall(r"\w+", text.lower())

    def upload(self, documents: list[Document]) -> None:
        """Tokenize and index documents for BM25 ranking."""
        if not documents:
            return

        self._documents.extend(documents)
        for doc in documents:
            text = f"{doc.title} {doc.content}"
            tokens = self._tokenize(text)
            self._doc_tokens.append(tokens)
            self._doc_lengths.append(len(tokens))

            unique_terms = set(tokens)
            for term in unique_terms:
                self._doc_frequencies[term] = self._doc_frequencies.get(term, 0) + 1

        total_docs = len(self._doc_lengths)
        self._avg_doc_len = (
            sum(self._doc_lengths) / total_docs if total_docs > 0 else 0.0
        )

        if log:
            log.success(
                f"BM25 Store: Indexed {len(documents)} documents (avg length: {self._avg_doc_len:.1f} words)"
            )

    def _idf(self, term: str) -> float:
        """Calculate Inverse Document Frequency (IDF) with smoothing."""
        n_q = self._doc_frequencies.get(term, 0)
        n_docs = len(self._documents)
        if n_docs == 0:
            return 0.0
        return math.log((n_docs - n_q + 0.5) / (n_q + 0.5) + 1.0)

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        """Rank and return top documents using Okapi BM25 scoring."""
        if not query or limit <= 0 or not self._documents:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores = [0.0] * len(self._documents)

        for term in query_tokens:
            idf = self._idf(term)
            if idf <= 0:
                continue

            for idx, tokens in enumerate(self._doc_tokens):
                tf = tokens.count(term)
                if tf == 0:
                    continue
                doc_len = self._doc_lengths[idx]
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (
                    1 - self.b + self.b * (doc_len / self.avg_dl_safe)
                )
                scores[idx] += idf * (numerator / denominator)

        scored_docs = [
            (score, doc) for score, doc in zip(scores, self._documents) if score > 0
        ]
        scored_docs.sort(key=lambda item: item[0], reverse=True)

        return [
            SearchResult(
                title=doc.title,
                content=doc.content,
                snippet=self._snippet(doc.content),
                score=round(score, 4),
                metadata=doc.metadata or {},
            )
            for score, doc in scored_docs[:limit]
        ]

    @property
    def avg_dl_safe(self) -> float:
        return self._avg_doc_len if self._avg_doc_len > 0 else 1.0

    @staticmethod
    def _snippet(content: str, length: int = 300) -> str:
        return f"{content[:length]}..." if len(content) > length else content
