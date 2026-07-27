"""HTTP Client Provider for remote Embedding Microservice."""

import requests
import os
from service.rag.base import EmbeddingProvider

try:
    from service.logger import log
except ImportError:
    log = None


class RemoteEmbeddingProvider(EmbeddingProvider):
    """Generates vector embeddings by calling the remote embedding microservice."""

    def __init__(self, service_url: str | None = None, timeout: float = 10.0):
        self.service_url = service_url or os.getenv("EMBEDDING_SERVICE_URL", "http://embedding-service:8001")
        self.timeout = timeout

    def embed(self, text: str) -> list[float]:
        text = text.strip()
        if not text:
            return []
        url = f"{self.service_url.rstrip('/')}/embed"
        try:
            resp = requests.post(url, json={"text": text}, timeout=self.timeout)
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
        url = f"{self.service_url.rstrip('/')}/embed_many"
        try:
            resp = requests.post(url, json={"texts": texts}, timeout=self.timeout * 2)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("embeddings", [])
            else:
                if log:
                    log.error(f"Remote embed_many service error: {resp.status_code}", resp.text[:100])
        except Exception as e:
            if log:
                log.error("Remote embedding service unreachable", str(e))
        return [[] for _ in texts]
