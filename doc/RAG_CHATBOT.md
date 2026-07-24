# RAG & Chatbot

The chatbot package in `backend/chatbot/` provides conversational QA grounded in news articles. The text embedding providers live in `backend/embeddings/`.

## Contents

- [Overview](#overview)
- [Database & Storage Integration (`db/`)](#database--storage-integration-db)
- [Text Embedding Layer (`embeddings/`)](#text-embedding-layer-embeddings)
- [Document Retrieval (`chatbot/rag/`)](#document-retrieval-chatbotrag)
- [Chatbot Service (`chatbot/service.py`)](#chatbot-service-chatbotservice)

## Overview

The chatbot is decoupled into three independent layers:
1. **Agent Provider (`backend/agents/`)**: Handles LLM chat completion.
2. **Embedding Provider (`backend/embeddings/`)**: Generates vector representations of articles and queries.
3. **Document Store (`backend/chatbot/rag/`)**: Indexes documents and performs semantic vector search.

## Database & Storage Integration (`db/`)

The RAG chatbot integrates with the database and storage repositories:

- **`FileStore`** (`db/storage.py`): In `chatbot/wiring.py`, `_load_and_upload_articles()` reads processed article JSONs via `FileStore.list_processed_files()` and `FileStore.read_json()` to populate the vector store with title, content, tags, and category metadata.
- **`MongoHandle`** (`db/mongo.py`): In `server/services/chat_service.py`, article details and user chat histories are fetched from `MongoHandle.collection("articles")` to supply additional context to the RAG response pipeline.

## Text Embedding Layer (`embeddings/`)

Embeddings are configured independently of the chat provider via `EMBEDDING_PROVIDER`:

```python
from embeddings import create_embedding_provider

embedder = create_embedding_provider("sentence_transformers")
vector = embedder.embed("India electric vehicle policy")
```

Available providers:
- `openai` / `foundry` — OpenAI or Foundry embeddings (`text-embedding-3-small`).
- `ollama` — Local Ollama embedding models (`nomic-embed-text`).
- `sentence_transformers` — In-process local PyTorch/SentenceTransformers embeddings.
- `huggingface` — Hugging Face feature extraction endpoint.
- `none` — Default base class implementation returning `[]` (no-op).

## Document Retrieval (`chatbot/rag/`)

Configured via `RAG_BACKEND`:

- `memory` — In-process vector store using `EmbeddingProvider` for similarity search.
- `bm25` — Pure Python Okapi BM25 lexical ranking store requiring **0 API calls, 0 vector embeddings, and 0 LLM costs**.
- `julep` — Julep managed document search platform.
- `none` — Default base class implementation returning `[]` search results (no-op).

## Chatbot Service (`chatbot/service.py`)

The orchestrator `ChatbotService` connects an `AgentProvider` and `DocumentStore`:

```python
from chatbot.service import ChatbotService
from chatbot.rag.factory import create_doc_store
from agents.factory import create_agent

chatbot = ChatbotService(
    agent=create_agent(),
    document_store=create_doc_store("memory"),
)

response = chatbot.get_response("Tell me about EV policy in India", user_id="user_123")
```
