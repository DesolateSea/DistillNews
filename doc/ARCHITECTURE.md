# DistillNews — Master Architecture & System Overview

DistillNews is a modular, AI-powered news aggregation, synthesis, and conversational QA platform. The project is structured as a full-stack monorepo with clear separation between the Next.js Frontend and Python Backend service stack.

---

## Contents

- [Monorepo Architecture](#monorepo-architecture)
- [Directory Layout](#directory-layout)
- [Core Subsystems](#core-subsystems)
  - [1. Frontend Tier (`frontend/`)](#1-frontend-tier-frontend)
  - [2. Backend API & Data Tier (`backend/server/` & `backend/db/`)](#2-backend-api--data-tier-backendserver--backenddb)
  - [3. News Ingestion Pipeline & TUI (`backend/pipeline/` & `backend/tui/`)](#3-news-ingestion-pipeline--tui-backendpipeline--backendtui)
  - [4. Provider-Neutral LLM Agents (`backend/agents/`)](#4-provider-neutral-llm-agents-backendagents)
  - [5. Conversational RAG & Retrieval (`backend/chatbot/` & `backend/embeddings/`)](#5-conversational-rag--retrieval-backendchatbot--backendembeddings)
- [Configuration & Environment (.env)](#configuration--environment-env)
- [Documentation Sitemap](#documentation-sitemap)

---

## Monorepo Architecture

The repository separates client-side browser user interface from server-side ingestion, TUI monitoring, and AI inference.

```
+-----------------------------------------------------------------------+
|                            FRONTEND TIER                              |
|                       Next.js / React / TypeScript                    |
+-----------------------------------------------------------------------+
                                   |
                              HTTP | REST API
                                   v
+-----------------------------------------------------------------------+
|                            BACKEND TIER                               |
|                                                                       |
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
|  +-----------------------------------------------------------------+  |
|            |                                             |            |
|            v                                             v            |
|  +-------------------+                         +-------------------+  |
|  | Agent Abstraction |                         | Embedding Layer   |  |
|  |  (agents/...)     |                         | (embeddings/...)  |  |
|  +-------------------+                         +-------------------+  |
+-----------------------------------------------------------------------+
```

---

## Directory Layout

```
DistillNews/
├── frontend/              # Next.js 14 Web Application
│   ├── app/               # App Router pages & views
│   ├── components/        # React UI component library
│   └── Dockerfile         # Standalone Node production container
│
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
```

---

## Core Subsystems

### 1. Frontend Tier (`frontend/`)

Built with Next.js (App Router), React, TypeScript, and Tailwind CSS. Features personal feed dashboards, article reader views, topic preferences, login/onboarding, and interactive RAG chat widgets.

### 2. Backend API & Data Tier (`backend/server/` & `backend/db/`)

Driven by FastAPI, `MongoHandle` (MongoDB), `RedisHandle` (Redis OTP cache), and `FileStore` (disk repository). Handles user authentication, personalized feed ranking based on dwell-time feedback loops, weather proxies, and article publication lifecycle.

### 3. News Ingestion Pipeline & TUI (`backend/pipeline/` & `backend/tui/`)

Crawls external web pages and news APIs (GNews, MediaStack, RapidAPI, Reddit, Core). Cleans raw HTML, calls LLM agents to classify items as news, extracts structured fields (title, publication date, category, location, summary), and saves normalized Markdown articles via `FileStore` with automatic `created_at` UTC timestamps.

Includes a **Textual Terminal User Interface (TUI)** in `backend/tui/` providing:

- Real-time progress monitoring per stage and item.
- Interactive hotkey controls (`f`, `s`, `g`, `p`, `x`, `a`, `q`).
- Non-blocking task cancellation via `PipelineRunner`.
- `ArticlesScreen` browser sorted by creation time **latest first**.

### 4. LLM Agent Providers (`backend/agents/`)

Abstracts LLM prompt execution behind `AgentProvider` and `create_agent()`. Supports interchangeable model providers (**OpenAI**, **Microsoft Azure Foundry**, **Ollama**, **Julep AI**, **Hugging Face**).

### 5. Conversational RAG & Retrieval (`backend/chatbot/` & `backend/embeddings/`)

Provides grounded conversational QA. `EmbeddingProvider` converts queries and articles into vector embeddings (OpenAI, Ollama, Sentence-Transformers, HuggingFace). `DocumentStore` indexes documents in vector backends (`InMemoryVectorStore`, `BM25DocStore`, `JulepDocStore`) for semantic or lexical context retrieval.

---

## Documentation Sitemap

Detailed subsystem documentation:

- [SERVER.md](SERVER.md) — FastAPI routes, domain services, and database repositories.
- [FRONTEND.md](FRONTEND.md) — Next.js frontend pages, component design, and client setup.
- [AGENT_PIPELINE.md](AGENT_PIPELINE.md) — Web scrapers, TUI dashboard, LLM extraction pipeline, and `FileStore`.
- [RAG_CHATBOT.md](RAG_CHATBOT.md) — Chatbot service, RAG document stores, and embedding providers.
