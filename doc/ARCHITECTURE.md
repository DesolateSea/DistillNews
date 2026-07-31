# DistillNews — System Architecture

This document provides a comprehensive technical overview of the DistillNews architecture, container topology, package layout, unified embedding service mechanism, and system boundaries.

---

## Architectural Principles

1. **Separation of Concerns**: The codebase is strictly partitioned into five top-level components:
   - `frontend/` — Next.js 14 Web Application (App Router, Tailwind CSS, LocalStorage Feature Flags)
   - `server/` — FastAPI REST Web Server (Auth, Feeds, User Preferences, Weather Proxy)
   - `service/` — Decoupled Business Logic & Domain Services (RAG, Chatbot, LLM Agents, ArticleStore)
   - `embedding_server/` — Standalone PyTorch / SentenceTransformers Vector Embedding Microservice
   - `pipeline/` — Independent News Ingestion, Extraction Engine & TUI Dashboard

2. **Unified Embedding Service Mechanism**: 
   A standalone FastAPI microservice (`embedding_server/`) exposes REST endpoints (`/embed` and `/embed_many`) running `sentence-transformers/all-MiniLM-L6-v2`. Both the **Ingestion Pipeline** (`pipeline/embeddings/providers/remote.py`) and the **Web Server / RAG Query Engine** (`service/rag/providers/remote_embedding.py`) connect to this service via `EMBEDDING_SERVICE_URL`. This isolates heavy PyTorch ML dependencies into a single lightweight container, preventing duplicate model loads and keeping web backend containers lightweight (~150MB).

3. **Container Isolation**: The backend web server container (`Dockerfile.backend`) and the ingestion pipeline container (`Dockerfile.pipeline`) are fully isolated. The web server does **not** import or execute `pipeline/` code, keeping production web deployments lightweight and fast.

4. **Provider Agnosticism**: All core AI capabilities (LLM agents, vector embeddings, and RAG document stores) are hidden behind abstract factory patterns, allowing seamless swapping of local and cloud backends without code modifications.

---

## System Architecture Diagram

```
+-----------------------------------------------------------------------+
|                          NEXT.JS FRONTEND                             |
|                        (frontend/ package)                            |
|  - Pages (Landing, Dashboard, News Reader, Preferences, Register)     |
|  - React Components (HeadlinesBanner, ChatFab, ThemeToggle, Cards)   |
|  - Feature Flags (LocalStorage per-flag state: ff_<id> = "true")     |
+-----------------------------------------------------------------------+
                                   |
                         (REST API / JSON)
                                   v
+-----------------------------------------------------------------------+
|                        FASTAPI WEB SERVER                             |
|                         (server/ package)                             |
|  - Routes (Auth, Feed, User Preferences, Chat, Weather Proxy)         |
|  - Services (user_service, article_service, chat_service)             |
|  - Middleware (JWT Auth, Security, CORS)                              |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                       DOMAIN SERVICES LAYER                           |
|                     (service/ package)                                |
|  - service/chatbot/ (Conversational RAG QA Service)                   |
|  - service/rag/     (BM25, Memory & Remote Document Stores)           |
|  - service/agents/  (OpenAI & Julep LLM Agents)                       |
|  - service/db/      (ArticleStore, AzureBlobStore, Mongo, Redis, File) |
|  - service/logger.py(Unified System Logger)                           |
+-----------------------------------------------------------------------+
            |                                           ^
            | (HTTP REST /embed)                        | (Query Vector)
            v                                           |
+-----------------------------------------------------------------------+
|                   STANDALONE EMBEDDING SERVER                         |
|                    (embedding_server/ package)                        |
|  - FastAPI REST API for SentenceTransformers vector embeddings        |
|  - Endpoints: GET /health, POST /embed, POST /embed_many              |
|  - Model: sentence-transformers/all-MiniLM-L6-v2                       |
+-----------------------------------------------------------------------+
            ^                                           ^
            | (Document Vectors)                        | (Article JSONs)
            |                                           |
+-----------------------------------------------------------------------+
|                   INDEPENDENT INGESTION PIPELINE                      |
|                         (pipeline/ package)                           |
|  - pipeline/scrapers/  (Web Scraping & Proxy Fetchers)                  |
|  - pipeline/parsers/   (HTML/API Article Extractors)                  |
|  - pipeline/embeddings/(Remote & ST Text Embeddings)                  |
|  - pipeline/tui/       (Terminal User Interface with Textual)         |
|  - pipeline/cli.py     (Independent CLI Entrypoint)                    |
+-----------------------------------------------------------------------+
```

---

## Container Topology

1. **`frontend` Container**: Node.js container serving the Next.js App Router UI (`frontend/Dockerfile`).
2. **`backend` Container**: Built via `Dockerfile.backend`. Copies `server/`, `service/`, `config.py`, `data/`, and `server/requirements.txt`. Strictly excludes `pipeline/` and heavy ML dependencies.
3. **`embedding-server` Container**: Built via `Dockerfile.embedding`. Runs the standalone FastAPI embedding service (`embedding_server/app.py` on port 8001).
4. **`mongo` Container**: MongoDB instance for persistent user profiles, preferences (`news_db.SNAPUsers`), and interaction bias weights.
5. **`redis` Container**: Redis instance for session state, OTP verification tokens, and API response caching.
6. **`pipeline` Container (Independent)**: Built via `Dockerfile.pipeline`. Operates independently outside the web server container via `pipeline/cli.py` or `pipeline/tui/`.

---

## Directory Layout

```
DistillNews/
├── frontend/              # Next.js 14 Web Application
│   ├── app/               # App Router pages (landing, dashboard, newsId, preferences, register)
│   ├── components/        # React UI components (HeadlinesBanner, ChatFab, ThemeToggle, etc.)
│   ├── lib/               # API clients & LocalStorage per-flag feature flag system
│   └── Dockerfile         # Standalone Node production container
│
├── server/                # FastAPI Web Server Tier
│   ├── app.py             # FastAPI entrypoint & application lifespan
│   ├── auth.py            # JWT authentication middleware
│   ├── security.py        # Password hashing & token utilities
│   ├── routes/            # API Route controllers (auth, feed, user, chat, weather)
│   └── services/          # Web domain services (user_service, chat_service, etc.)
│
├── service/               # Core shared business logic & data repositories
│   ├── articles.py        # Shared article service (loading, ranking, pagination)
│   ├── blob/              # File and Blob storage engines (ArticleStore, FileStore, Azure)
│   ├── db/                # Database connection handles (MongoDB, Redis)
│   ├── chatbot/           # Conversational QA service & wiring
│   ├── rag/               # Retrieval-Augmented Generation backends (BM25, Memory, Remote)
│   ├── agents/            # Provider-neutral LLM agent abstraction (OpenAI, Julep)
│   └── logger.py          # Centralized system logger
│
├── embedding_server/      # Standalone Embedding Microservice
│   ├── app.py             # FastAPI embedding server (/embed, /embed_many)
│   └── requirements.txt   # PyTorch & SentenceTransformers dependencies
│
├── pipeline/              # Independent News Ingestion & CLI Pipeline
│   ├── scrapers/          # Web crawlers, fetchers, and proxy rotation
│   ├── parsers/           # Article body & news metadata extractors
│   ├── sources/           # External API handlers (GNews, MediaStack, RapidAPI, Reddit)
│   ├── embeddings/        # Text embedding providers (OpenAI, ST, Remote HTTP)
│   ├── tui/               # Terminal User Interface for pipeline monitoring
│   ├── cli.py             # CLI runner (`python pipeline/cli.py [scrape|extract|generate|tui]`)
│   ├── extraction.py      # LLM classification & article extraction pipeline
│   ├── generate.py        # End-to-end article generation runner
│   └── requirements.txt   # Pipeline Python dependencies
│
├── data/                  # Storage repository for raw, api_data, and processed JSON articles
├── doc/                   # Master System Documentation Suite
├── config.py              # Centralized environment configuration loader
├── Dockerfile.backend     # Lightweight web backend production container build
├── Dockerfile.embedding   # Standalone text embedding microservice build
└── Dockerfile.pipeline    # Independent ingestion pipeline container build
```

---

## Unified Embedding Service Architecture

In previous versions, Sentence Transformers was loaded inside individual Python processes, causing heavy memory consumption (~1.5GB PyTorch per process) and slow startup times. 

The unified architecture resolves this via the **`embedding_server`** microservice:

1. **Service Specification**: Runs FastAPI on port `8001` with `sentence-transformers/all-MiniLM-L6-v2`.
2. **Endpoints**:
   - `GET /health` — Returns status, loaded model name, and memory state.
   - `POST /embed` — Accepts `{"text": "..."}`, returns 384-dimensional normalized vector.
   - `POST /embed_many` — Accepts `{"texts": ["...", "..."]}`, returns batch normalized vectors.
3. **Consumers**:
   - **Query Embedding Provider** (`service/rag/providers/remote_embedding.py`): Called by the backend RAG chatbot during conversational QA and semantic vector search.
   - **Ingestion Pipeline Provider** (`pipeline/embeddings/providers/remote.py`): Called by the ingestion pipeline during batch article embedding generation (`EMBEDDING_PROVIDER=remote`).

---

## Core System Abstractions

### 1. LLM Agent Abstraction (`service/agents/`)

The `AgentProvider` abstract base class decouples LLM generation from specific providers. Agents render prompt templates from YAML files and output standardized `CompletionResult` objects.

| Key | Implementation | Target Provider | Use Case |
| :--- | :--- | :--- | :--- |
| `openai` | `OpenAIAgent` | OpenAI API / Azure Foundry | Production standard LLM generation (`gpt-4o`, `gpt-4o-mini`) |
| `julep` | `JulepAgent` | Julep AI Platform | Multi-step agent execution & managed workflows |

### 2. Article Storage Abstraction (`service/db/`)

The `ArticleStore` base class decouples article persistence from underlying storage technologies:

| Key | Implementation | Storage Target | Description |
| :--- | :--- | :--- | :--- |
| `file` | `FileArticleStore` | `data/processed_articles/` | Local JSON file storage for local development |
| `azure` | `AzureBlobArticleStore` | Azure Blob Container | High-availability cloud blob storage for production |
