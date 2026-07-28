"""Shared interface for text embedding providers with default no-op behavior."""


class EmbeddingProvider:
    """Convert text into vectors suitable for semantic retrieval.

    By default, returns empty vectors when no embedding model is configured.
    """

    def embed(self, text: str) -> list[float]:
        """Return an embedding vector for one text input."""
        return []

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        """Return embeddings in the same order as *texts*.

        Providers with batch endpoints may override this to make one request.
        """
        return [self.embed(text) for text in texts]
