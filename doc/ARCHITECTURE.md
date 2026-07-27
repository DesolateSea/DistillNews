# DistillNews — Master Architecture & System Overview

DistillNews is a modular, AI-powered news aggregation, synthesis, and conversational QA platform. The codebase is decoupled into distinct top-level modules (`frontend/`, `server/`, `service/`, and `pipeline/`) ensuring strict separation of concerns between web delivery, shared domain services, and ingestion pipelines.

---

## Contents

- [Decoupled Architecture](#decoupled-architecture)
- [Container Topology](#container-topology)
- [Directory Layout](#directory-layout)
- [Core Subsystems](#core-subsystems)
  - [1. Frontend Tier (`frontend/`)](#1-frontend-tier-frontend)
<<<<<<< HEAD
  - [2. Backend API & Data Tier (`backend/server/` & `backend/db/`)](#2-backend-api--data-tier-backendserver--backenddb)
  - [3. News Ingestion Pipeline & TUI (`backend/pipeline/` & `backend/tui/`)](#3-news-ingestion-pipeline--tui-backendpipeline--backendtui)
  - [4. Provider-Neutral LLM Agents (`backend/agents/`)](#4-provider-neutral-llm-agents-backendagents)
  - [5. Conversational RAG & Retrieval (`backend/chatbot/` & `backend/embeddings/`)](#5-conversational-rag--retrieval-backendchatbot--backendembeddings)
- [Configuration & Environment (.env)](#configuration--environment-env)
=======
  - [2. Web Server (`server/`)](#2-web-server-server)
  - [3. Domain Services (`service/`)](#3-domain-services-service)
    - [Chatbot & RAG (`service/chatbot/` & `service/rag/`)](#chatbot--rag-servicechatbot--servicerag)
    - [LLM Agents (`service/agents/`)](#llm-agents-serviceagents)
    - [Database Handles & FileStore (`service/db/`)](#database-handles--filestore-servicedb)
  - [4. Independent Ingestion Pipeline (`pipeline/`)](#4-independent-ingestion-pipeline-pipeline)
>>>>>>> 582a92f (refactor: The code base has sperated the pipelines completely from the)
- [Documentation Sitemap](#documentation-sitemap)

---

## Decoupled Architecture

<<<<<<< HEAD
The repository separates client-side browser user interface from server-side ingestion, TUI monitoring, and AI inference.
=======
The system decouples client presentation, web server routing, core domain services, and background data ingestion pipelines into standalone top-level packages:
>>>>>>> 582a92f (refactor: The code base has sperated the pipelines completely from the)

```
+-----------------------------------------------------------------------+
|                            FRONTEND TIER                              |
|                       Next.js / React / TypeScript                    |
+-----------------------------------------------------------------------+
                                   |
                              HTTP | REST API
                                   v
+-----------------------------------------------------------------------+
|                        BACKEND CONTAINER                              |
|                                                                       |
<<<<<<< HEAD
|  +-------------------+  +-------------------+  +-------------------+  |
|  |  FastAPI Server   |  | Ingestion & TUI   |  |    RAG Chatbot    |  |
|  |  (server/app.py)  |  |  (pipeline/tui)   |  |   (chatbot/...)   |  |
|  +-------------------+  +-------------------+  +-------------------+  |
|            |                      |                      |            |
|            v                      v                      v            |
|  +-----------------------------------------------------------------+  |
|  |                     REPOSITORY & DB LAYER                       |  |
|  |  - MongoHandle (news_db.articles, news_db.SNAPUsers)            |  |
|  |  - RedisHandle (OTP Session Store)                              |  |
|  |  - FileStore   (Article JSONs with created_at, Raw HTML, API)   |  |
=======
|  +-----------------------------------------------------------------+  |
|  |                       FastAPI Web Server                        |  |
|  |                         (server/app.py)                         |  |
>>>>>>> 582a92f (refactor: The code base has sperated the pipelines completely from the)
|  +-----------------------------------------------------------------+  |
|                                  |                                    |
|                                  v                                    |
|  +-----------------------------------------------------------------+  |
|  |                       DOMAIN SERVICES LAYER                     |  |
|  |                     (service/ package)                          |  |
|  |  - service/chatbot/ (Conversational QA Service)                 |  |
|  |  - service/rag/     (BM25, Memory & Julep Document Stores)       |  |
|  |  - service/agents/  (OpenAI, Julep, Ollama, HF Agents)         |  |
|  |  - service/db/      (MongoHandle, RedisHandle, FileStore)        |  |
|  |  - service/logger.py(Unified System Logger)                    |  |
|  +-----------------------------------------------------------------+  |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|                   INDEPENDENT INGESTION PIPELINE                      |
|                         (pipeline/ package)                           |
|  - pipeline/scrapers/  (Web Scraping & Proxy Fetchers)               |
|  - pipeline/parsers/   (HTML/API Article Extractors)                  |
|  - pipeline/embeddings/(Text Embeddings & SentenceTransformers)       |
|  - pipeline/tui/       (Terminal User Interface)                      |
|  - pipeline/cli.py     (Independent CLI Entrypoint)                    |
+-----------------------------------------------------------------------+
```

---

## Container Topology

1. **`frontend` Container**: Standalone Node.js container serving the Next.js App Router UI.
2. **`backend` Container**: Built via `Dockerfile.backend`. Copies ONLY `server/`, `service/`, `config.py`, and `requirements-backend.txt`. Strictly excludes `pipeline/` and heavy ML dependencies.
3. **`mongo` Container**: MongoDB instance for persistent articles and user profiles.
4. **`redis` Container**: Redis instance for session state, OTP verification, and caching.
5. **`pipeline` Container (Independent)**: Built via `Dockerfile.pipeline`. Operates independently outside the web server container via `pipeline/cli.py` or `pipeline/tui/`.

---

## Directory Layout

```
DistillNews/
├── frontend/              # Next.js 14 Web Application
│   ├── app/               # App Router pages & views
│   ├── components/        # React UI component library
│   └── Dockerfile         # Standalone Node production container
│
<<<<<<< HEAD
├── backend/               # Python Backend Service Stack
│   ├── server/            # FastAPI web server & endpoints
│   ├── pipeline/          # News scraping, parsing, extraction, PipelineRunner
│   ├── tui/               # Textual Terminal User Interface dashboard
│   ├── chatbot/           # Conversational RAG & retrieval logic
│   │
│   ├── db/                # Unified Storage handles (MongoHandle, RedisHandle, FileStore)
│   ├── agents/            # LLM agent provider abstraction (OpenAI/Foundry, Ollama, Julep, HF)
│   ├── embeddings/        # Text embedding providers (SentenceTransformers, OpenAI, etc.)
│   │
│   ├── tests/             # Pytest test suite & fixtures
│   ├── data/              # Runtime files (api_data, raw HTML, processed JSONs)
│   │
│   ├── cli.py             # CLI entry point (fetch, scrape, generate, tui, run-all)
│   ├── config.py          # Centralized configuration (.env loader)
│   ├── requirements.txt   # Python dependencies
│   └── Dockerfile         # Standalone backend container build
│
├── doc/                   # System Documentation Suite
│   ├── ARCHITECTURE.md    # Master architecture & system sitemap (this file)
│   ├── SERVER.md          # FastAPI endpoints, services, & DB handles
│   ├── FRONTEND.md        # Web application pages & client components
│   ├── AGENT_PIPELINE.md  # Pipeline scraping, TUI dashboard, LLM extraction & FileStore
│   └── RAG_CHATBOT.md     # Conversational QA, RAG backends, & embeddings
│
├── .env                   # Environment variable configuration
└── .env.example           # Documented template for environment settings
=======
├── server/                # FastAPI Web Server Tier
│   ├── app.py             # FastAPI entrypoint & application lifespan
│   ├── auth.py            # JWT authentication middleware
│   ├── security.py        # Password hashing & token utilities
│   ├── routes/            # API Route controllers (auth, feed, user, chat, weather)
│   ├── services/          # Web domain services (user_service, article_service, etc.)
│   ├── models/            # Pydantic request/response schemas
│   └── utils/             # Recommendation & sorting utilities
│
├── service/               # Shared Domain Services Tier
│   ├── chatbot/           # Conversational QA service & wiring
│   ├── rag/               # Retrieval-Augmented Generation backends (BM25, Memory, Julep)
│   ├── agents/            # Provider-neutral LLM agent abstraction
│   ├── db/                # Database handles (MongoDB, Redis, FileStore repository)
│   └── logger.py          # Centralized system logger
│
├── pipeline/              # Independent News Ingestion & CLI Pipeline
│   ├── scrapers/          # Web crawlers, fetchers, and proxy rotation
│   ├── parsers/           # Article body & news metadata extractors
│   ├── sources/           # External API handlers (GNews, MediaStack, RapidAPI, Reddit)
│   ├── embeddings/        # Independent text embedding providers (OpenAI, ST, Ollama, HF)
│   ├── tui/               # Terminal User Interface for pipeline monitoring
│   ├── cli.py             # CLI runner (`python pipeline/cli.py [scrape|extract|generate|tui]`)
│   ├── extraction.py      # LLM classification & article extraction pipeline
│   ├── generate.py        # End-to-end article generation runner
│   └── scrape.py          # Standalone web scraping runner
│
├── tests/                 # Pytest test suite & fixtures
├── doc/                   # Master System Documentation Suite
├── config.py              # Centralized environment configuration loader
├── requirements.txt       # Shared master Python dependencies
├── requirements-backend.txt # Lightweight web backend dependencies (No PyTorch/sentence-transformers)
├── requirements-pipeline.txt# Pipeline scraping & ingestion dependencies
├── Dockerfile.backend     # Lightweight web backend production container build
└── Dockerfile.pipeline    # Independent ingestion pipeline container build
>>>>>>> 582a92f (refactor: The code base has sperated the pipelines completely from the)
```

---

## Core Subsystems

### 1. Frontend Tier (`frontend/`)

Built with Next.js (App Router), React, TypeScript, and Tailwind CSS. Features personal feed dashboards, article reader views, topic preferences, login/onboarding, and interactive RAG chat widgets.

### 2. Web Server (`server/`)

FastAPI web application exposing RESTful API endpoints for authentication, personalized feed discovery, dwell-time feedback loop processing, weather proxies, and chat queries.

<<<<<<< HEAD
### 3. News Ingestion Pipeline & TUI (`backend/pipeline/` & `backend/tui/`)

Crawls external web pages and news APIs (GNews, MediaStack, RapidAPI, Reddit, Core). Cleans raw HTML, calls LLM agents to classify items as news, extracts structured fields (title, publication date, category, location, summary), and saves normalized Markdown articles via `FileStore` with automatic `created_at` UTC timestamps.

Includes a **Textual Terminal User Interface (TUI)** in `backend/tui/` providing:

- Real-time progress monitoring per stage and item.
- Interactive hotkey controls (`f`, `s`, `g`, `p`, `x`, `a`, `q`).
- Non-blocking task cancellation via `PipelineRunner`.
- `ArticlesScreen` browser sorted by creation time **latest first**.
=======
### 3. Domain Services (`service/`)

Decoupled domain business capabilities:
- **`service/chatbot/`**: Conversational QA engine orchestrating query intent filtering, context retrieval, and grounded response synthesis.
- **`service/rag/`**: Modular document store interface supporting `BM25DocStore` (zero-cost lexical), `InMemoryVectorStore` (vector search), and `JulepDocStore`.
- **`service/agents/`**: LLM agent provider abstraction supporting interchangeable backends (**OpenAI**, **Microsoft Azure Foundry**, **Ollama**, **Julep AI**, **Hugging Face**).
- **`service/db/`**: Centralized database repositories (`MongoHandle`, `RedisHandle`, and `FileStore`).
>>>>>>> 582a92f (refactor: The code base has sperated the pipelines completely from the)

### 4. Independent Ingestion Pipeline (`pipeline/`)

<<<<<<< HEAD
Abstracts LLM prompt execution behind `AgentProvider` and `create_agent()`. Supports interchangeable model providers (**OpenAI**, **Microsoft Azure Foundry**, **Ollama**, **Julep AI**, **Hugging Face**).

### 5. Conversational RAG & Retrieval (`backend/chatbot/` & `backend/embeddings/`)

Provides grounded conversational QA. `EmbeddingProvider` converts queries and articles into vector embeddings (OpenAI, Ollama, Sentence-Transformers, HuggingFace). `DocumentStore` indexes documents in vector backends (`InMemoryVectorStore`, `BM25DocStore`, `JulepDocStore`) for semantic or lexical context retrieval.
=======
Autonomous pipeline for discovering, fetching, cleaning, classifying, and saving structured news articles. Features:
- Web scraping and API collection across GNews, MediaStack, RapidAPI, and Reddit.
- Modular text embedding providers in `pipeline/embeddings/` (including local SentenceTransformers).
- Interactive Terminal User Interface in `pipeline/tui/`.
- Independent CLI execution via `python pipeline/cli.py`.
>>>>>>> 582a92f (refactor: The code base has sperated the pipelines completely from the)

---

## Documentation Sitemap

Detailed subsystem documentation:

- [SERVER.md](SERVER.md) — FastAPI routes, domain services, and database repositories.
- [FRONTEND.md](FRONTEND.md) — Next.js frontend pages, component design, and client setup.
- [AGENT_PIPELINE.md](AGENT_PIPELINE.md) — Web scrapers, TUI dashboard, LLM extraction pipeline, and `FileStore`.
- [RAG_CHATBOT.md](RAG_CHATBOT.md) — Chatbot service, RAG document stores, and embedding providers.
