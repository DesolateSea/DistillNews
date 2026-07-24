# Agent & News Ingestion Pipeline

The news ingestion pipeline in `backend/pipeline/` collects raw news articles, cleans HTML and social posts, calls LLM agents to classify and extract structured news metadata, and formats articles as Markdown. Its entry points are `backend/pipeline/generate.py` and `backend/pipeline/scrape.py`.

All storage access (article JSONs, raw HTML, API responses, deduplication checks) is managed via the unified `FileStore` repository (`backend/db/storage.py`).

## Contents

- [Overview](#overview)
- [LLM Agent Layer (`agents/`)](#llm-agent-layer-agents)
- [Storage Layer (`db/storage.py`)](#storage-layer-dbstoragepy)
- [Running the Pipeline](#running-the-pipeline)

## Overview

The pipeline operates independently from the web server and chatbot. It processes raw API responses and web scrapes into structured JSON files stored in `backend/data/processed/` via `FileStore`.

## LLM Agent Layer (`agents/`)

The agent layer in `backend/agents/` decouples LLM completion calls from provider implementations:

```python
from agents import create_agent

agent = create_agent()  # Selected by AGENT_PROVIDER env var
result = agent.complete_from_template("pipeline/prompts/is_news.yaml", input_data)
```

Supported providers:
- `openai` / `foundry` — Microsoft Foundry or OpenAI endpoints.
- `ollama` — Local Ollama instances.
- `julep` — Julep AI platform task execution.
- `huggingface` — Hugging Face Inference API.

## Storage Layer (`db/storage.py`)

All file interactions are encapsulated behind the `FileStore` repository handle:

```python
from db import FileStore

# Deduplication check
if FileStore.article_exists(article_id):
    print("Article already processed")

# Save normalized article
FileStore.save_processed_article(parsed_data, article_id=article_id)

# Load target URLs config or fixture JSON
targets = FileStore.read_json("pipeline/scrapers/config/target_urls.json")
```

## Running the Pipeline

Run web scrapers:
```bash
cd backend
python3 -m pipeline.scrape
```

Run article generator:
```bash
cd backend
python3 -m pipeline.generate
```
