"""HTTP Client Embedding Provider that delegates vector generation to the remote Embedding Microservice."""

from config import config
from pipeline.embeddings.base import EmbeddingProvider
from service.rag.providers.remote_embedding import RemoteEmbeddingProvider as RemoteClient


class RemoteEmbeddingProvider(EmbeddingProvider):
    """Generates text vector embeddings by making REST calls to the standalone embedding_server microservice."""

    def __init__(self, service_url: str | None = None, timeout: float = 10.0):
        url = service_url or config.EMBEDDING_SERVICE_URL
        self._client = RemoteClient(service_url=url, timeout=timeout)

    def embed(self, text: str) -> list[float]:
        return self._client.embed(text)

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return self._client.embed_many(texts)
