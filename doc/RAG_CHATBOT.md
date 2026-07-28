# RAG & Chatbot

The chatbot package in `service/chatbot/` provides conversational QA grounded in news articles. The retrieval engines live in `service/rag/`, and text embedding providers live in `pipeline/embeddings/`.

## Contents

- [Overview](#overview)
- [Database & Storage Integration (`service/db/`)](#database--storage-integration-servicedb)
- [Text Embedding Layer (`pipeline/embeddings/`)](#text-embedding-layer-pipelineembeddings)
- [Document Retrieval (`service/rag/`)](#document-retrieval-servicerag)
- [Chatbot Service (`service/chatbot/service.py`)](#chatbot-service-servicechatbotservicepy)

## Overview

The chatbot is decoupled into three independent layers:

1. **Agent Provider (`service/agents/`)**: Handles LLM chat completion.
2. **Embedding Provider (`pipeline/embeddings/`)**: Generates vector representations of articles and queries.
3. **Document Store (`service/rag/`)**: Indexes documents and performs semantic vector search.

## Database & Storage Integration (`service/db/`)

The RAG chatbot integrates with the database and storage repositories:

- **`ArticleStore`** (`service/db/article_store.py`): In `service/chatbot/wiring.py`, `_load_and_upload_articles()` reads processed articles via `article_store.load_all_articles()` to populate the document store with title, content, tags, and category metadata.
- **`MongoHandle`** (`service/db/mongo.py`): User chat histories and user account profiles are stored in MongoDB.
- **`FileStore`** (`service/db/filestore.py`): Used for reading low-level local JSON test fixtures and configuration files.

## Text Embedding Layer (`pipeline/embeddings/`)

Embeddings are configured independently of the chat provider via `EMBEDDING_PROVIDER`:

```python
from pipeline.embeddings import create_embedding_provider

embedder = create_embedding_provider("sentence_transformers")
vector = embedder.embed("India electric vehicle policy")
```

Available providers:

- `openai` / `foundry` — OpenAI or Foundry embeddings (`text-embedding-3-small`).
- `sentence_transformers` — In-process local PyTorch/SentenceTransformers embeddings (`all-MiniLM-L6-v2`).
- `remote` — Standalone HTTP REST microservice (`embedding_server`).
- `none` — Default base class implementation returning `[]` (no-op).

## Document Retrieval (`service/rag/`)

Configured via `RAG_BACKEND`:

- `memory` — In-process vector store using `EmbeddingProvider` for similarity search.
- `bm25` — Pure Python Okapi BM25 lexical ranking store.
- `julep` — Julep managed document search platform.
- `none` — Default base class implementation returning `[]` search results (no-op).

## Chatbot Service (`service/chatbot/service.py`)

The orchestrator `ChatbotService` connects an `AgentProvider` and `DocumentStore`:

```python
from service.chatbot.service import ChatbotService
from service.rag.factory import create_doc_store
from service.agents.factory import create_agent

chatbot = ChatbotService(
    agent=create_agent(),
    document_store=create_doc_store("memory"),
)

response = chatbot.get_response("Tell me about EV policy in India", user_id="user_123")
```
