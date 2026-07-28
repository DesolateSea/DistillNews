# DistillNews — System Architecture

This document provides a high-level technical overview of the DistillNews architecture, container topology, package layout, and key system boundaries.

---

## Architectural Principles

1. **Separation of Concerns**: The codebase is strictly partitioned into four top-level components:
   - `frontend/` — Next.js 14 Web Application
   - `server/` — FastAPI REST Web Server
   - `service/` — Decoupled Business Logic & Domain Services (RAG, Chatbot, Agents, DB)
   - `embedding_server/` — Standalone PyTorch/SentenceTransformers Vector Embedding Microservice
   - `pipeline/` — Independent News Ingestion & Extraction Engine

2. **Container Boundary**: The backend web server container (`Dockerfile.backend`) and the ingestion pipeline container (`Dockerfile.pipeline`) are fully isolated. The web server does **not** import or execute `pipeline/` code, keeping production web deployments lightweight and fast.

3. **Provider Agnosticism**: All core AI capabilities (LLM agents, vector embeddings, and RAG document stores) are hidden behind abstract factory patterns, allowing seamless swapping of local and cloud backends without code modifications.

---

## System Architecture Diagram

```
+-----------------------------------------------------------------------+
|                          NEXT.JS FRONTEND                             |
|                        (frontend/ package)                            |
|  - Pages (Feed, Reader, Chat, Preferences, Login)                     |
|  - React Components (ArticleCard, ChatWidget, Header, Search)          |
+-----------------------------------------------------------------------+
                                   |
                         (REST API / JSON)
                                   v
+-----------------------------------------------------------------------+
|                        FASTAPI WEB SERVER                             |
|                         (server/ package)                             |
|  - Routes (Auth, Feed, User, Chat, Weather)                           |
|  - Services (user_service, article_service, chat_service)             |
|  - Middleware (JWT Auth, Security, CORS)                              |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                       DOMAIN SERVICES LAYER                           |
|                     (service/ package)                                |
|  - service/chatbot/ (Conversational QA Service)                       |
|  - service/rag/     (BM25, Memory & Julep Document Stores)             |
|  - service/agents/  (OpenAI & Julep AI Agents)                        |
|  - service/db/      (ArticleStore, AzureBlobStore, Mongo, Redis, File) |
|  - service/logger.py(Unified System Logger)                           |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|                   STANDALONE EMBEDDING SERVER                         |
|                    (embedding_server/ package)                        |
|  - FastAPI REST API for SentenceTransformers vector embeddings        |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|                   INDEPENDENT INGESTION PIPELINE                      |
|                         (pipeline/ package)                           |
|  - pipeline/scrapers/  (Web Scraping & Proxy Fetchers)                     |
|  - pipeline/parsers/   (HTML/API Article Extractors)                  |
|  - pipeline/embeddings/(Text Embeddings & SentenceTransformers)       |
|  - pipeline/tui/       (Terminal User Interface)                      |
|  - pipeline/cli.py     (Independent CLI Entrypoint)                    |
+-----------------------------------------------------------------------+
```

---

## Container Topology

1. **`frontend` Container**: Standalone Node.js container serving the Next.js App Router UI.
2. **`backend` Container**: Built via `Dockerfile.backend`. Copies `server/`, `service/`, `config.py`, `data/`, and `server/requirements.txt`. Strictly excludes `pipeline/` and heavy ML dependencies.
3. **`embedding-server` Container**: Built via `Dockerfile.embedding`. Runs the standalone FastAPI embedding service (`embedding_server/app.py`).
4. **`mongo` Container**: MongoDB instance for persistent articles, user profiles, and bookmarks.
5. **`redis` Container**: Redis instance for session state, OTP verification, and caching.
6. **`pipeline` Container (Independent)**: Built via `Dockerfile.pipeline`. Operates independently outside the web server container via `pipeline/cli.py` or `pipeline/tui/`.

---

## Directory Layout

```
DistillNews/
├── frontend/              # Next.js 14 Web Application
│   ├── app/               # App Router pages & views
│   ├── components/        # React UI component library
│   └── Dockerfile         # Standalone Node production container
│
├── server/                # FastAPI Web Server Tier
│   ├── app.py             # FastAPI entrypoint & application lifespan
│   ├── auth.py            # JWT authentication middleware
│   ├── security.py        # Password hashing & token utilities
│   ├── routes/            # API Route controllers (auth, feed, user, chat, weather)
│   ├── services/          # Web domain services (user_service, article_service, etc.)
│   ├── models/            # Pydantic request/response schemas
│   ├── utils/             # Recommendation & sorting utilities
│   └── requirements.txt   # Web backend Python dependencies
│
├── service/               # Shared Domain Services Tier
│   ├── chatbot/           # Conversational QA service & wiring
│   ├── rag/               # Retrieval-Augmented Generation backends (BM25, Memory, Julep)
│   ├── agents/            # Provider-neutral LLM agent abstraction
│   ├── db/                # Database handles (MongoDB, Redis, FileStore repository)
│   └── logger.py          # Centralized system logger
│
├── embedding_server/      # Standalone Embedding Microservice
│   ├── app.py             # FastAPI embedding server
│   └── requirements.txt   # Microservice dependencies
│
├── pipeline/              # Independent News Ingestion & CLI Pipeline
│   ├── scrapers/          # Web crawlers, fetchers, and proxy rotation
│   ├── parsers/           # Article body & news metadata extractors
│   ├── sources/           # External API handlers (GNews, MediaStack, RapidAPI, Reddit)
│   ├── embeddings/        # Independent text embedding providers (OpenAI, ST)
│   ├── tui/               # Terminal User Interface for pipeline monitoring
│   ├── cli.py             # CLI runner (`python pipeline/cli.py [scrape|extract|generate|tui]`)
│   ├── extraction.py      # LLM classification & article extraction pipeline
│   ├── generate.py        # End-to-end article generation runner
│   ├── scrape.py          # Standalone web scraping runner
│   └── requirements.txt   # Pipeline Python dependencies
│
├── data/                  # Storage repository for raw, api_data, and processed JSON articles
├── tests/                 # Pytest test suite & fixtures
├── doc/                   # Master System Documentation Suite
├── config.py              # Centralized environment configuration loader
├── Dockerfile.backend     # Lightweight web backend production container build
├── Dockerfile.embedding   # Standalone text embedding microservice build
└── Dockerfile.pipeline    # Independent ingestion pipeline container build
```

---

## Core System Abstractions

### 1. LLM Agent Abstraction (`service/agents/`)

The `AgentProvider` abstract base class decouples LLM generation from specific providers. Agents render prompt templates from YAML files and output standardized `CompletionResult` objects.

| Key | Implementation | Target Provider | Use Case |
| :--- | :--- | :--- | :--- |
| `openai` | `OpenAIAgent` | OpenAI API / Azure Foundry | Production standard LLM generation (`gpt-4o`, `gpt-4o-mini`) |
| `julep` | `JulepAgent` | Julep AI Platform | Multi-step agent execution & managed workflows |

---

### 2. Text Vector Embedding Abstraction (`pipeline/embeddings/` & `embedding_server/`)

The `EmbeddingProvider` interface normalizes vector generation across local in-process models, remote microservices, and cloud endpoints.

| Key | Implementation | Target Backend | Use Case |
| :--- | :--- | :--- | :--- |
| `sentence_transformers` | `SentenceTransformersEmbeddingProvider` | PyTorch / SentenceTransformers | Local in-process embeddings (`all-MiniLM-L6-v2`) |
| `remote` | `RemoteEmbeddingProvider` | Standalone `embedding_server` | REST client microservice execution without local PyTorch overhead |
| `openai` / `foundry` | `OpenAIEmbeddingProvider` | OpenAI / Azure Foundry API | Cloud vector embeddings (`text-embedding-3-small`) |
| `none` | `EmbeddingProvider` | No-op fallback | Zero-dependency fallback returning empty vectors `[]` |

---

### 3. RAG & Document Store Abstraction (`service/rag/`)

The `DocumentStore` base class defines unified `upload()` and `search()` operations for grounding chatbot QA.

| Key | Implementation | Strategy | Characteristics |
| :--- | :--- | :--- | :--- |
| `memory` | `InMemoryVectorStore` | Dense Vector Search | Cosine similarity ranking over embedded document vectors |
| `bm25` | `BM25DocStore` | Lexical Search | Fast keyword & term frequency ranking (`rank-bm25`) |
| `julep` | `JulepDocStore` | Cloud Managed Vector Index | Remote vector RAG index hosted on Julep AI |
| `none` | `DocumentStore` | No-op | Direct LLM responses without article retrieval |

---

### 4. Pipeline Data Sources (`pipeline/sources/` & `scrapers/`)

News discovery and scraping modules integrated into the pipeline runner.

| Source Name | Module | Target API / Technology | Status |
| :--- | :--- | :--- | :--- |
| `gnews` | `pipeline.sources.gnews` | Google News RSS & API | Enabled |
| `media_stack` | `pipeline.sources.media_stack` | MediaStack News REST API | Enabled |
| `news_org` | `pipeline.sources.news_org` | NewsAPI.org topic crawler | Enabled |
| `rapid_news` | `pipeline.sources.rapid_news` | RapidAPI News Feed | Enabled |
| `core` | `pipeline.sources.core` | CORE Open Access Research API | Enabled |
| `scrape` | `pipeline.scrapers` | BeautifulSoup4 HTML Web Crawler | Enabled |
| `reddit` | `pipeline.sources.reddit` | Reddit API (PRAW crawler) | Disabled by default |

---

### 5. Storage & Database Layer (`service/db/`)

Repository layer handling persistent state, cloud article stores, transient cache, and raw JSON document storage.

| Storage Engine | Module / Class | Data Managed |
| :--- | :--- | :--- |
| **ArticleStore** | `ArticleStore` / `create_article_store()` | Abstract interface for article persistence (`azure` or `file`) |
| **Azure Blob Store** | `AzureBlobArticleStore` (`azure_blob_store.py`) | Cloud storage container (`processed-articles`) for processed news JSONs |
| **FileArticleStore** | `FileArticleStore` (`filestore.py`) | Local disk repository storing processed JSON articles in `data/processed/` |
| **MongoDB** | `MongoHandle` (`mongo.py`) | Async persistent store for user accounts (`SNAPUsers`) and interaction metrics |
| **Redis** | `RedisHandle` (`redis.py`) | Fast key-value store for session tokens, OTPs, and rate limiting |
| **FileStore** | `FileStore` (`filestore.py`) | Low-level file I/O for raw HTML scrapes and raw API payloads |

---

## Core Subsystems Overview

### 1. Frontend Tier (`frontend/`)

Built with Next.js 14 (App Router), React, TypeScript, and Tailwind CSS. Features personal feed dashboards, article reader views, topic preferences, login/onboarding, and interactive RAG chat widgets.

### 2. Web Server (`server/`)

FastAPI web application exposing RESTful API endpoints for authentication, personalized feed discovery, dwell-time feedback loop processing, weather proxies, and chat queries.

### 3. Domain Services (`service/`)

Decoupled domain business capabilities:
- **`service/chatbot/`**: Conversational QA engine orchestrating query intent filtering, context retrieval, and grounded response synthesis.
- **`service/rag/`**: Modular document store interface.
- **`service/agents/`**: LLM agent provider abstraction.
- **`service/db/`**: Centralized database repositories (`MongoHandle`, `RedisHandle`, and `FileStore`).

### 4. Independent Ingestion Pipeline (`pipeline/`)

Autonomous pipeline for discovering, fetching, cleaning, classifying, and saving structured news articles. Features:
- Web scraping and API collection across GNews, MediaStack, RapidAPI, and Reddit.
- Modular text embedding providers in `pipeline/embeddings/`.
- Interactive Terminal User Interface in `pipeline/tui/`.
- Independent CLI execution via `python pipeline/cli.py`.

---

## Documentation Sitemap

- [SERVER.md](SERVER.md) — FastAPI routes, domain services, and database repositories.
- [FRONTEND.md](FRONTEND.md) — Next.js frontend pages, component design, and client setup.
- [AGENT_PIPELINE.md](AGENT_PIPELINE.md) — Web scrapers, parsers, LLM extraction pipeline, and `FileStore`.
- [RAG_CHATBOT.md](RAG_CHATBOT.md) — Chatbot service, RAG document stores, and embedding providers.
