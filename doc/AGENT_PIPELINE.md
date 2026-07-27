# Agent & News Ingestion Pipeline & TUI Dashboard

<<<<<<< HEAD
The news ingestion pipeline in `backend/pipeline/` collects raw news articles, cleans HTML and social posts, calls LLM agents to classify and extract structured news metadata, and formats articles as Markdown.

In addition to programmatic CLI commands (`backend/cli.py`), the platform includes a **Textual Terminal User Interface (TUI)** in `backend/tui/` for real-time monitoring, live progress tracking, source toggling, and article browsing.

All storage access (article JSONs, raw HTML, API responses, deduplication checks, and creation timestamps) is managed via the unified `FileStore` repository (`backend/db/storage.py`).

---
=======
The news ingestion pipeline in `pipeline/` collects raw news articles, cleans HTML and social posts, calls LLM agents to classify and extract structured news metadata, and formats articles as Markdown. Its entry points are `pipeline/cli.py`, `pipeline/tui/`, `pipeline/generate.py`, and `pipeline/scrape.py`.

All storage access (article JSONs, raw HTML, API responses, deduplication checks) is managed via the unified `FileStore` repository (`service/db/storage.py`).
>>>>>>> 582a92f (refactor: The code base has sperated the pipelines completely from the)

## Contents

- [Overview](#overview)
<<<<<<< HEAD
- [Terminal User Interface (TUI) (`tui/`)](#terminal-user-interface-tui-tui)
- [Pipeline Event Runner (`pipeline/runner.py`)](#pipeline-event-runner-pipelinerunnerpy)
- [LLM Agent Layer (`agents/`)](#llm-agent-layer-agents)
- [Storage & Timestamp Metadata (`db/storage.py`)](#storage--timestamp-metadata-dbstoragepy)
- [Running the Pipeline & TUI](#running-the-pipeline--tui)

---
=======
- [LLM Agent Layer (`service/agents/`)](#llm-agent-layer-serviceagents)
- [Storage Layer (`service/db/storage.py`)](#storage-layer-servicedbstoragepy)
- [Running the Pipeline & TUI](#running-the-pipeline--tui)
>>>>>>> 582a92f (refactor: The code base has sperated the pipelines completely from the)

## Overview

The pipeline operates independently from the web server and chatbot. It processes raw API responses and web scrapes into structured JSON files stored in `pipeline/data/processed/` via `FileStore`.

<<<<<<< HEAD
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

## Terminal User Interface (TUI) (`tui/`)

The TUI provides a dashboard built with **Textual** (`backend/tui/app.py`):

- **Live Stage Progress Bars**: Visual progress bars and item-level detail labels for **Fetch**, **Scrape**, and **Generate** stages.
- **Rich Log Panel**: Streamed real-time logs with badge color-coding (INFO, SUCCESS, WARN, ERROR) and full item progress (`Item 1/37: Title...`).
- **Source Controls**: Single-line toggle indicators (`ON` / `OFF`) for configured news sources (`reddit`, `rapid_news`, `gnews`, `media_stack`, `news_org`, `core`).
- **Cooperative Task Cancellation**: Pressing `x` or clicking **Stop Tasks** instantly cancels active worker threads using `PipelineRunner` cancellation tokens without blocking the UI.
- **Article Inspector Screen (`ArticlesScreen`)**: Pressing `a` opens a interactive `DataTable` listing processed articles sorted by latest first. Highlighted rows show full rich-text formatted article details.

### TUI Keybindings

|  Key  | Action          | Description                                                     |
| :---: | :-------------- | :-------------------------------------------------------------- |
|  `f`  | Fetch Sources   | Runs API fetchers for enabled sources                           |
|  `s`  | Scrape Articles | Scrapes target web URLs                                         |
|  `g`  | Generate News   | Runs AI extraction and markdown formatting                      |
|  `p`  | Run All         | Executes full pipeline sequentially (Fetch ➔ Scrape ➔ Generate) |
|  `x`  | Stop Tasks      | Instantly cancels active pipeline execution                     |
|  `a`  | Browse Articles | Opens interactive article browser sorted latest first           |
|  `q`  | Quit            | Gracefully cancels workers and exits TUI                        |
| `Esc` | Back            | Exits `ArticlesScreen` back to main dashboard                   |

---

## Pipeline Event Runner (`pipeline/runner.py`)

`PipelineRunner` encapsulates pipeline execution and dispatches structured events to UI listeners:

```python
from pipeline.runner import PipelineRunner, PipelineEvent, StageStarted, StageProgress, StageCompleted, LogEvent

def handle_event(event: PipelineEvent):
    if isinstance(event, StageStarted):
        print(f"Started {event.stage} stage ({event.total} items)")
    elif isinstance(event, StageProgress):
        print(f"[{event.stage}] {event.current}/{event.total}: {event.detail}")

runner = PipelineRunner(callback=handle_event, stop_checker=lambda: cancellation_requested)
runner.run_all()
```

### Event Hierarchy

- `StageStarted(stage, total)` — Emitted when a stage begins with total count.
- `StageProgress(stage, current, total, detail)` — Emitted during item-by-item processing.
- `StageCompleted(stage)` — Emitted when a stage finishes.
- `LogEvent(badge, message, detail)` — Emitted for log output.

---

## LLM Agent Layer (`agents/`)
=======
## LLM Agent Layer (`service/agents/`)
>>>>>>> 582a92f (refactor: The code base has sperated the pipelines completely from the)

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

<<<<<<< HEAD
---

## Article Storage (`db/storage.py`)
=======
## Storage Layer (`service/db/storage.py`)
>>>>>>> 582a92f (refactor: The code base has sperated the pipelines completely from the)

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

<<<<<<< HEAD
```json
{
  "title": "Example Article Title",
  "publication_date": "2026-07-25",
  "created_at": "2026-07-25T08:15:00.123456+00:00",
  "category": "Technology",
  "content": "Markdown article body..."
}
```

---

## Running the Pipeline & TUI

### Launching the TUI Dashboard

```bash
backend/cli.py
=======
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
>>>>>>> 582a92f (refactor: The code base has sperated the pipelines completely from the)
```

To run via CLI, see `backend/cli.py --help`
