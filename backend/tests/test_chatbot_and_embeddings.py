"""Offline checks for the chatbot, retrieval, and embedding boundaries using pytest."""

from pathlib import Path
from types import SimpleNamespace
import pytest

from agents.base import CompletionResult
from chatbot import ChatbotService
from embeddings import EmbeddingProvider, create_embedding_provider
from embeddings.providers.openai import OpenAIEmbeddingProvider
from embeddings.providers.sentence_transformers import (
    SentenceTransformersEmbeddingProvider,
)
from chatbot.rag.base import Document, DocumentStore, SearchResult
from chatbot.rag.factory import create_doc_store


class KeywordEmbedder(EmbeddingProvider):
    """Small deterministic embedder used to test vector-store composition."""

    def embed(self, text: str) -> list[float]:
        text = text.lower()
        return [float("climate" in text), float("sports" in text)]


class StaticDocumentStore(DocumentStore):
    def upload(self, documents: list[Document]) -> None:
        self.documents = documents

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        return [
            SearchResult(
                title="Climate report",
                content="Full climate article",
                snippet="Climate article excerpt",
            )
        ]


class FakeAgent:
    def __init__(self):
        self.calls = []

    def complete_from_template(self, template_path, input_data):
        self.calls.append((Path(template_path).name, input_data))
        if Path(template_path).name == "filter_prompt.yaml":
            return CompletionResult(content="climate")
        return CompletionResult(content=f"Grounded answer: {input_data['content']}")


def test_memory_store_uses_injected_embedder_and_preserves_metadata():
    store = create_doc_store("memory", embedder=KeywordEmbedder())
    store.upload(
        [
            Document(
                title="Sports update",
                content="sports news",
                metadata={"category": "sports"},
            ),
            Document(
                title="Climate update",
                content="climate news",
                metadata={"category": "environment"},
            ),
        ]
    )

    result = store.search("climate", limit=1)[0]
    assert result.title == "Climate update"
    assert result.metadata == {"category": "environment"}
    assert result.score == 1.0


def test_noop_embedding_provider_makes_no_vectors():
    assert create_embedding_provider("none").embed("anything") == []


def test_embedding_backends_are_not_rag_backends():
    for backend in ("openai", "foundry", "ollama", "huggingface", "in_memory"):
        with pytest.raises(ValueError, match="Available: memory, julep, none"):
            create_doc_store(backend)


def test_openai_embedder_batches_long_inputs_without_provider_access():
    calls = []

    class FakeEmbeddings:
        def create(self, *, model, input):
            calls.append((model, input))
            return SimpleNamespace(
                data=[
                    SimpleNamespace(index=index, embedding=[float(index)])
                    for index, _ in reversed(list(enumerate(input)))
                ]
            )

    embedder = object.__new__(OpenAIEmbeddingProvider)
    embedder.model = "local-test-model"
    embedder._client = SimpleNamespace(embeddings=FakeEmbeddings())

    embeddings = embedder.embed_many([f"document {index}" for index in range(51)])

    assert [len(inp) for _, inp in calls] == [50, 1]
    assert embeddings[0] == [0.0]
    assert embeddings[-1] == [0.0]


def test_sentence_transformers_provider_uses_a_local_model():
    class FakeModel:
        def __init__(self):
            self.calls = []

        def encode(self, texts, **kwargs):
            self.calls.append((texts, kwargs))
            return [[1, 2], [3, 4]]

    model = FakeModel()
    embedder = create_embedding_provider(
        "sentence_transformers", model_name="local-model", model=model
    )

    embeddings = embedder.embed_many(["first\ntext", "second text"])

    assert isinstance(embedder, SentenceTransformersEmbeddingProvider)
    assert embeddings == [[1.0, 2.0], [3.0, 4.0]]
    assert model.calls[0][0] == ["first text", "second text"]
    assert model.calls[0][1]["normalize_embeddings"] is True


def test_chatbot_only_depends_on_agent_and_document_store():
    agent = FakeAgent()
    chatbot = ChatbotService(
        agent=agent,
        document_store=StaticDocumentStore(),
        prompts_dir=Path("chatbot/prompts"),
    )

    response = chatbot.get_response("What happened?", user_id="reader-1")

    assert response == "Grounded answer: Climate article excerpt"
    assert agent.calls[0][0] == "filter_prompt.yaml"
    assert agent.calls[1][1]["content"] == "Climate article excerpt"
    assert agent.calls[1][1]["memory"] == ""
