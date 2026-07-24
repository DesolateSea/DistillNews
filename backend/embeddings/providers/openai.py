"""OpenAI-compatible embedding provider, including Foundry endpoints."""

from config import config
from embeddings.base import EmbeddingProvider


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Create vectors through an OpenAI-compatible embeddings endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        from openai import OpenAI

        self._api_key = api_key or config.OPENAI_API_KEY
        self._base_url = base_url or config.OPENAI_BASE_URL
        self.model = model or config.OPENAI_EMBEDDING_MODEL

        if not self._api_key:
            raise ValueError("An API key is required. Set FOUNDRY_API_KEY or OPENAI_API_KEY.")

        client_kwargs: dict = {"api_key": self._api_key}
        if self._base_url:
            client_kwargs["base_url"] = self._base_url
        self._client = OpenAI(**client_kwargs)

    def embed(self, text: str) -> list[float]:
        text = text.replace("\n", " ").strip()
        if not text:
            return []
        response = self._client.embeddings.create(model=self.model, input=text)
        return response.data[0].embedding

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        cleaned = [text.replace("\n", " ").strip() or " " for text in texts]
        if not cleaned:
            return []

        embeddings = []
        for start in range(0, len(cleaned), 50):
            response = self._client.embeddings.create(
                model=self.model,
                input=cleaned[start : start + 50],
            )
            embeddings.extend(
                item.embedding for item in sorted(response.data, key=lambda item: item.index)
            )
        return embeddings
