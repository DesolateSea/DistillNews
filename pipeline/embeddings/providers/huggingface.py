"""Hugging Face feature-extraction embedding provider."""

import json
import urllib.request

from config import config
from pipeline.embeddings.base import EmbeddingProvider


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    """Create vectors through Hugging Face's feature-extraction endpoint."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._api_key = api_key or config.HUGGINGFACE_API_KEY
        self.model = model or config.HUGGINGFACE_EMBEDDING_MODEL

    def embed(self, text: str) -> list[float]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        request = urllib.request.Request(
            f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.model}",
            data=json.dumps({"inputs": text.replace("\n", " ").strip() or " "}).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request) as response:
                result = json.loads(response.read().decode("utf-8"))
        except Exception as error:
            raise RuntimeError(
                f"Hugging Face embedding failed for model {self.model!r}."
            ) from error

        if isinstance(result, list) and result and isinstance(result[0], list):
            dimensions = len(result[0])
            return [
                sum(token[dimension] for token in result) / len(result)
                for dimension in range(dimensions)
            ]
        if isinstance(result, list) and all(isinstance(value, (int, float)) for value in result):
            return result
        raise RuntimeError(f"Hugging Face returned an unexpected embedding response for {self.model!r}.")
