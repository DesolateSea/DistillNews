"""Local embedding provider powered by Sentence Transformers."""

from config import config
from embeddings.base import EmbeddingProvider


class SentenceTransformersEmbeddingProvider(EmbeddingProvider):
    """Generate embeddings locally with a Sentence Transformers model.

    The model is loaded only when this provider is selected. On first use,
    Sentence Transformers may download the selected model into its local cache.
    """

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        batch_size: int = 32,
        model=None,
    ):
        self.model_name = model_name or config.SENTENCE_TRANSFORMERS_EMBEDDING_MODEL
        self._batch_size = batch_size

        if model is not None:
            self._model = model
            return

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError(
                "Local Sentence Transformers embeddings require the optional "
                "'sentence-transformers' dependency. Install requirements.txt first."
            ) from error

        selected_device = device or config.SENTENCE_TRANSFORMERS_DEVICE
        model_kwargs = {"device": selected_device} if selected_device else {}
        self._model = SentenceTransformer(self.model_name, **model_kwargs)

    def embed(self, text: str) -> list[float]:
        text = text.replace("\n", " ").strip()
        if not text:
            return []
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        cleaned = [text.replace("\n", " ").strip() or " " for text in texts]
        vectors = self._model.encode(
            cleaned,
            batch_size=self._batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [[float(value) for value in vector] for vector in vectors]
