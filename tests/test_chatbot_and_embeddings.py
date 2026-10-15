"""Offline checks for the chatbot, retrieval, and embedding boundaries using pytest."""

from pathlib import Path
from types import SimpleNamespace
import pytest

from service.agents.base import CompletionResult
from service.chatbot import ChatbotService
from pipeline.embeddings import EmbeddingProvider, create_embedding_provider
from pipeline.embeddings.providers.openai import OpenAIEmbeddingProvider
from pipeline.embeddings.providers.sentence_transformers import (
    SentenceTransformersEmbeddingProvider,
)
from service.rag.base import Document, DocumentStore, SearchResult
from service.rag.factory import create_doc_store
from service.agents.base import ToolCallingProvider, ToolDefinition, AgentMessage


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


class FakeToolCallingAgent(ToolCallingProvider):
    def __init__(self):
        self.calls = []

    def complete(self, system_prompt: str, user_prompt: str) -> CompletionResult:
        return CompletionResult(content="dummy")

    def chat_with_tools(
        self,
        messages: list[AgentMessage],
        tools: list[ToolDefinition] | None = None,
        tool_choice: str | dict = "auto",
    ) -> AgentMessage:
        self.calls.append(("chat_with_tools", messages))
        return AgentMessage(role="assistant", content="Grounded answer: Climate article excerpt")


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


def test_bm25_doc_store_lexical_retrieval():
    store = create_doc_store("bm25")
    store.upload(
        [
            Document(
                title="Electric Vehicles Policy",
                content="India introduces new EV manufacturing subsidies and tariff reductions.",
                metadata={"category": "auto"},
            ),
            Document(
                title="Cricket World Cup",
                content="India wins cricket match against Australia in final overs.",
                metadata={"category": "sports"},
            ),
        ]
    )

    results = store.search("electric vehicle EV subsidies", limit=1)
    assert len(results) == 1
    assert results[0].title == "Electric Vehicles Policy"
    assert results[0].score > 0.0


def test_noop_embedding_provider_makes_no_vectors():
    assert create_embedding_provider("none").embed("anything") == []


@pytest.mark.parametrize("model,parameter", [("gpt-5-mini", "max_completion_tokens"), ("gpt-4o-mini", "max_tokens")])
def test_chat_provider_token_limit_matches_model(model, parameter):
    from service.agents.providers.openai import OpenAIAgent
    agent = object.__new__(OpenAIAgent)
    agent._model = model
    assert agent._token_limit() == {parameter: 2048}


@pytest.mark.parametrize("suffix", ["", "/", "/responses", "/responses/", "/chat/completions"])
def test_chat_provider_normalizes_operation_urls(suffix):
    from service.agents.providers.openai import OpenAIAgent
    root = "https://example.services.ai.azure.com/openai/v1"
    assert OpenAIAgent._normalize_base_url(root + suffix) == root + "/"


def test_remote_embeddings_use_configured_api_and_bounded_batches(monkeypatch):
    monkeypatch.setenv("EMBEDDING_SERVICE_URL", "http://127.0.0.1:8001")
    monkeypatch.setenv("EMBEDDING_REQUEST_TIMEOUT", "45")
    embedder = create_embedding_provider("remote", batch_size=2)
    calls = []

    def post(url, *, json, timeout):
        calls.append((url, json, timeout))
        return SimpleNamespace(status_code=200, json=lambda: {"embeddings": [[float(t)] for t in json["texts"]]})

    monkeypatch.setattr(embedder._client.session, "post", post)
    assert embedder.embed_many(["1", "2", "3"]) == [[1.0], [2.0], [3.0]]
    assert [len(call[1]["texts"]) for call in calls] == [2, 1]
    assert all(call[0] == "http://127.0.0.1:8001/embed_many" and call[2] == 45 for call in calls)


def test_remote_embeddings_preserve_alignment_on_invalid_response(monkeypatch):
    embedder = create_embedding_provider("remote", batch_size=2)
    monkeypatch.setattr(embedder._client.session, "post", lambda *a, **kw: SimpleNamespace(
        status_code=200, json=lambda: {"embeddings": [[1.0]]}))
    assert embedder.embed_many(["one", "two"]) == [[], []]


def test_embedding_backends_are_not_rag_backends():
    for backend in ("openai", "foundry", "sentence_transformers", "in_memory"):
        with pytest.raises(ValueError, match="Available: memory, bm25, none"):
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
    agent = FakeToolCallingAgent()
    chatbot = ChatbotService(
        agent=agent,
        document_store=StaticDocumentStore(),
    )

    response = chatbot.get_response("What happened?", user_id="reader-1")

    assert response == "Grounded answer: Climate article excerpt"
    assert len(agent.calls) > 0
    assert agent.calls[0][0] == "chat_with_tools"
    # messages[0] = system prompt, messages[1] = user message
    messages = agent.calls[0][1]
    user_messages = [m for m in messages if m.role == "user"]
    assert len(user_messages) == 1
    assert user_messages[0].content == "What happened?"
