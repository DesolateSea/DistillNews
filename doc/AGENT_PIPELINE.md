# Ingestion Pipeline & TUI Dashboard

The news ingestion pipeline in `pipeline/` crawls external sources, extracts news content, generates vector embeddings, classifies articles using LLM agents, and publishes normalized articles to `ArticleStore`.

---

## Processing Flow

```
External Sources (News APIs / Reddit / Scrapers)
                     │
                     ▼
             Parsers & HTML Cleaners
                     │
                     ▼
          LLM News Classifier Agent
                     │
                     ▼
    Embedding Generation (EMBEDDING_PROVIDER=remote)
  [Calls embedding_server:8001 /embed_many]
                     │
                     ▼
       ArticleStore (Azure Blob / Local File)
```

---

## Unified Embedding Integration

The pipeline supports generating document vector embeddings using the standalone **`embedding_server`** microservice:

```bash
# Run extraction using the shared embedding_server microservice
python pipeline/cli.py generate --storage azure --embedding-provider remote
```

### Provider Selection (`pipeline/embeddings/factory.py`)

- `remote` / `embedding_server` (`pipeline/embeddings/providers/remote.py`): Connects to `EMBEDDING_SERVICE_URL` (`http://embedding-server:8001`). Reuses the exact same PyTorch embedding container as the web server, avoiding duplicate model loading in the pipeline container.
- `sentence_transformers` (`pipeline/embeddings/providers/sentence_transformers.py`): In-process SentenceTransformers model.
- `openai` / `foundry` (`pipeline/embeddings/providers/openai.py`): OpenAI embeddings (`text-embedding-3-small`).

---

## Terminal User Interface (TUI) (`pipeline/tui/`)

The pipeline includes an interactive TUI built with **Textual** (`pipeline/tui/app.py`):

- **Live Stage Progress**: Real-time progress bars for **Fetch**, **Scrape**, and **Generate** stages.
- **Log Stream**: Color-coded log panel (`INFO`, `SUCCESS`, `WARN`, `ERROR`).
- **Source Toggles**: Interactive `ON` / `OFF` toggles for sources (`gnews`, `media_stack`, `rapid_news`, `reddit`, `news_org`).
- **Article Inspector (`a` key)**: Displays interactive table of processed articles with metadata (`Category`, `Pub Date`, `ID`).

---

## CLI Entrypoint Usage (`pipeline/cli.py`)

```bash
# Launch interactive TUI
python pipeline/cli.py tui --storage azure

# Run web scrapers
python pipeline/cli.py scrape

# Run news extraction pipeline
python pipeline/cli.py extract --storage file

# Run end-to-end generation
python pipeline/cli.py generate --storage azure --embedding-provider remote

# Inspect saved articles
python pipeline/cli.py articles --storage azure -n 20
```
