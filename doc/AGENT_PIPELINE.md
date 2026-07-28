# Agent & News Ingestion Pipeline & TUI Dashboard

The news ingestion pipeline in `pipeline/` collects raw news articles, cleans HTML and social posts, calls LLM agents to classify and extract structured news metadata, and formats articles as Markdown. Its entry points are `pipeline/cli.py`, `pipeline/tui/`, `pipeline/generate.py`, and `pipeline/scrape.py`.

All storage access (article JSONs, raw HTML, API responses, deduplication checks) is managed via the unified `FileStore` repository (`service/db/storage.py`).

## Contents

- [Overview](#overview)
- [Terminal User Interface (TUI) (`pipeline/tui/`)](#terminal-user-interface-tui-pipelinetui)
- [LLM Agent Layer (`service/agents/`)](#llm-agent-layer-serviceagents)
- [Storage Layer (`service/db/storage.py`)](#storage-layer-servicedbstoragepy)
- [Running the Pipeline & TUI](#running-the-pipeline--tui)

---

## Overview

The pipeline operates independently from the web server and chatbot. It processes raw API responses and web scrapes into structured JSON files stored in `data/processed/` via `FileStore`.

```
Raw API Payloads / Scrapes  ──>  Parser & HTML Cleaner
                                         │
                                         ▼
                                 LLM News Classifier
                                         │
                                         ▼
                                 Structured Extractor
                                         │
                                         ▼
                                 FileStore (.json)
```

---

## Terminal User Interface (TUI) (`pipeline/tui/`)

The TUI provides a dashboard built with **Textual** (`pipeline/tui/app.py`):

- **Live Stage Progress Bars**: Visual progress bars and item-level detail labels for **Fetch**, **Scrape**, and **Generate** stages.
- **Rich Log Panel**: Streamed real-time logs with badge color-coding (INFO, SUCCESS, WARN, ERROR).
- **Source Controls**: Single-line toggle indicators (`ON` / `OFF`) for configured news sources (`reddit`, `rapid_news`, `gnews`, `media_stack`, `news_org`, `core`).
- **Article Inspector Screen**: Pressing `a` opens an interactive table listing processed articles.

---

## LLM Agent Layer (`service/agents/`)

The agent layer in `service/agents/` decouples LLM completion calls from provider implementations:

```python
from service.agents import create_agent

agent = create_agent()  # Selected by AGENT_PROVIDER env var
result = agent.complete_from_template("pipeline/prompts/is_news.yaml", input_data)
```

Supported providers:

- `openai` / `foundry` — Microsoft Azure Foundry or OpenAI endpoints.
- `ollama` — Local Ollama instances.
- `julep` — Julep AI platform task execution.
- `huggingface` — Hugging Face Inference API.

---

## Storage Layer (`service/db/storage.py`)

All file interactions are encapsulated behind the `FileStore` repository handle:

```python
from service.db import FileStore

# Deduplication check
if FileStore.article_exists(article_id):
    print("Article already processed")

# Save normalized article
FileStore.save_processed_article(parsed_data, article_id=article_id)

# Load target URLs config or fixture JSON
targets = FileStore.read_json("pipeline/scrapers/config/target_urls.json")
```

---

## Running the Pipeline & TUI

Use the independent CLI entrypoint `pipeline/cli.py`:

```bash
# Launch interactive Terminal User Interface (TUI)
python pipeline/cli.py tui

# Run web scrapers
python pipeline/cli.py scrape

# Run news extraction
python pipeline/cli.py extract

# Run full pipeline generation
python pipeline/cli.py generate
```
