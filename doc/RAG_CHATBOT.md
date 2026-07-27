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
<<<<<<< HEAD

1. **Agent Provider (`backend/agents/`)**: Handles LLM chat completion.
2. **Embedding Provider (`backend/embeddings/`)**: Generates vector representations of articles and queries.
3. **Document Store (`backend/chatbot/rag/`)**: Indexes documents and performs semantic vector search.
=======
1. **Agent Provider (`service/agents/`)**: Handles LLM chat completion.
2. **Embedding Provider (`pipeline/embeddings/`)**: Generates vector representations of articles and queries.
3. **Document Store (`service/rag/`)**: Indexes documents and performs semantic vector search.
>>>>>>> 582a92f (refactor: The code base has sperated the pipelines completely from the)

## Database & Storage Integration (`service/db/`)

The RAG chatbot integrates with the database and storage repositories:

- **`FileStore`** (`service/db/storage.py`): In `service/chatbot/wiring.py`, `_load_and_upload_articles()` reads processed article JSONs via `FileStore.list_processed_files()` and `FileStore.read_json()` to populate the vector store with title, content, tags, and category metadata.
- **`MongoHandle`** (`service/db/mongo.py`): In `server/services/chat_service.py`, article details and user chat histories are fetched from `MongoHandle.collection("articles")` to supply additional context to the RAG response pipeline.

## Text Embedding Layer (`pipeline/embeddings/`)

Embeddings are configured independently of the chat provider via `EMBEDDING_PROVIDER`:

```python
from pipeline.embeddings import create_embedding_provider

embedder = create_embedding_provider("sentence_transformers")
vector = embedder.embed("India electric vehicle policy")
```

Available providers:

- `openai` / `foundry` — OpenAI or Foundry embeddings (`text-embedding-3-small`).
- `ollama` — Local Ollama embedding models (`nomic-embed-text`).
- `sentence_transformers` — In-process local PyTorch/SentenceTransformers embeddings.
- `huggingface` — Hugging Face feature extraction endpoint.
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
