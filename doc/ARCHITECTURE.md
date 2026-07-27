# DistillNews — Master Architecture & System Overview

DistillNews is a modular, AI-powered news aggregation, synthesis, and conversational QA platform. The codebase is decoupled into distinct top-level modules (`frontend/`, `server/`, `service/`, and `pipeline/`) ensuring strict separation of concerns between web delivery, shared domain services, and ingestion pipelines.

## Contents

- [Decoupled Architecture](#decoupled-architecture)
- [Container Topology](#container-topology)
- [Directory Layout](#directory-layout)
- [Core Subsystems](#core-subsystems)
  - [1. Frontend Tier (`frontend/`)](#1-frontend-tier-frontend)
  - [2. Web Server (`server/`)](#2-web-server-server)
  - [3. Domain Services (`service/`)](#3-domain-services-service)
    - [Chatbot & RAG (`service/chatbot/` & `service/rag/`)](#chatbot--rag-servicechatbot--servicerag)
    - [LLM Agents (`service/agents/`)](#llm-agents-serviceagents)
    - [Database Handles & FileStore (`service/db/`)](#database-handles--filestore-servicedb)
  - [4. Independent Ingestion Pipeline (`pipeline/`)](#4-independent-ingestion-pipeline-pipeline)
- [Documentation Sitemap](#documentation-sitemap)

---

## Decoupled Architecture

The system decouples client presentation, web server routing, core domain services, and background data ingestion pipelines into standalone top-level packages:

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
|  +-----------------------------------------------------------------+  |
|  |                       FastAPI Web Server                        |  |
|  |                         (server/app.py)                         |  |
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
2. **`backend` Container**: Built via `Dockerfile.backend`. Copies ONLY `server/`, `service/`, `config.py`, `data/`, and `requirements-backend.txt`. Strictly excludes `pipeline/` and heavy ML dependencies.
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
├── data/                  # Storage repository for raw, api_data, and processed JSON articles
├── tests/                 # Pytest test suite & fixtures
├── doc/                   # Master System Documentation Suite
├── config.py              # Centralized environment configuration loader
├── requirements.txt       # Shared master Python dependencies
├── requirements-backend.txt # Lightweight web backend dependencies (No PyTorch/sentence-transformers)
├── requirements-pipeline.txt# Pipeline scraping & ingestion dependencies
├── Dockerfile.backend     # Lightweight web backend production container build
└── Dockerfile.pipeline    # Independent ingestion pipeline container build
```

---

## Core Subsystems

### 1. Frontend Tier (`frontend/`)

Built with Next.js (App Router), React, TypeScript, and Tailwind CSS. Features personal feed dashboards, article reader views, topic preferences, login/onboarding, and interactive RAG chat widgets.

### 2. Web Server (`server/`)

FastAPI web application exposing RESTful API endpoints for authentication, personalized feed discovery, dwell-time feedback loop processing, weather proxies, and chat queries.

### 3. Domain Services (`service/`)

Decoupled domain business capabilities:
- **`service/chatbot/`**: Conversational QA engine orchestrating query intent filtering, context retrieval, and grounded response synthesis.
- **`service/rag/`**: Modular document store interface supporting `BM25DocStore` (zero-cost lexical), `InMemoryVectorStore` (vector search), and `JulepDocStore`.
- **`service/agents/`**: LLM agent provider abstraction supporting interchangeable backends (**OpenAI**, **Microsoft Azure Foundry**, **Ollama**, **Julep AI**, **Hugging Face**).
- **`service/db/`**: Centralized database repositories (`MongoHandle`, `RedisHandle`, and `FileStore`).

### 4. Independent Ingestion Pipeline (`pipeline/`)

Autonomous pipeline for discovering, fetching, cleaning, classifying, and saving structured news articles. Features:
- Web scraping and API collection across GNews, MediaStack, RapidAPI, and Reddit.
- Modular text embedding providers in `pipeline/embeddings/` (including local SentenceTransformers).
- Interactive Terminal User Interface in `pipeline/tui/`.
- Independent CLI execution via `python pipeline/cli.py`.

---

## Documentation Sitemap

Detailed subsystem documentation:

- [SERVER.md](SERVER.md) — FastAPI routes, domain services, and database repositories.
- [FRONTEND.md](FRONTEND.md) — Next.js frontend pages, component design, and client setup.
- [AGENT_PIPELINE.md](AGENT_PIPELINE.md) — Web scrapers, parsers, LLM extraction pipeline, and `FileStore`.
- [RAG_CHATBOT.md](RAG_CHATBOT.md) — Chatbot service, RAG document stores, and embedding providers.
