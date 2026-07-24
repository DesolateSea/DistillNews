"""Local Ollama embedding provider."""

import json
import urllib.request

from config import config
from embeddings.base import EmbeddingProvider


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Create vectors through a locally running Ollama instance."""

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self._base_url = (base_url or config.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or config.OLLAMA_EMBEDDING_MODEL

    def embed(self, text: str) -> list[float]:
        payload = {
            "model": self.model,
            "prompt": text.replace("\n", " ").strip() or " ",
        }
        request = urllib.request.Request(
            f"{self._base_url}/api/embeddings",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request) as response:
                return json.loads(response.read().decode("utf-8")).get("embedding", [])
        except Exception as error:
            raise RuntimeError(
                f"Ollama embedding failed for model {self.model!r}. "
                "Ensure Ollama is running and the embedding model is pulled."
            ) from error
