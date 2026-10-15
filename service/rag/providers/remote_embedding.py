"""HTTP Client Provider for remote Embedding Microservice."""

import requests
from config import config
from service.rag.base import EmbeddingProvider

try:
    from service.logger import log
except ImportError:
    log = None


class RemoteEmbeddingProvider(EmbeddingProvider):
    """Generates vector embeddings by calling the remote embedding microservice."""

    def __init__(self, service_url: str | None = None, timeout: float | None = None, batch_size: int = 32):
        self.service_url = service_url or config.EMBEDDING_SERVICE_URL
        self.timeout = timeout if timeout is not None else config.EMBEDDING_REQUEST_TIMEOUT
        if self.timeout <= 0 or batch_size <= 0:
            raise ValueError("Embedding timeout and batch size must be positive")
        self.batch_size = batch_size
        self.session = requests.Session()

    def embed(self, text: str) -> list[float]:
        text = text.strip()
        if not text:
            return []
        url = f"{self.service_url.rstrip('/')}/embed"
        try:
            resp = self.session.post(url, json={"text": text}, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("embedding", [])
            else:
                if log:
                    log.error(f"Remote embedding service error: {resp.status_code}", resp.text[:100])
        except Exception as e:
            if log:
                log.error("Remote embedding service unreachable", str(e))
        return []

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start:start + self.batch_size]
            embeddings.extend(self._embed_batch(batch))
        return embeddings

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        url = f"{self.service_url.rstrip('/')}/embed_many"
        try:
            resp = self.session.post(url, json={"texts": texts}, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                vectors = data.get("embeddings", [])
                if not isinstance(vectors, list) or len(vectors) != len(texts):
                    raise ValueError("Embedding service returned the wrong number of vectors")
                return vectors
            else:
                if log:
                    log.error(f"Remote embed_many service error: {resp.status_code}", resp.text[:100])
        except Exception as e:
            if log:
                log.error("Remote embedding service unreachable", str(e))
        return [[] for _ in texts]
