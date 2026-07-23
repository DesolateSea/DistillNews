# DistillNews Agent & Environment Setup Guide

This guide details all environment variable configurations supported by DistillNews for setting up agent providers, RAG backends, news source APIs, and system services.

All configurations are loaded from a `.env` file in the project root by `src/config.py`.

---

## 1. Overview & Provider Selection

DistillNews supports multiple AI providers for its multi-agent news processing pipelines and RAG search assistant. You can specify the active agent provider and RAG backend using the following variables:

```env
# Active agent provider (options: openai, julep, ollama, huggingface)
AGENT_PROVIDER=openai

# Active RAG backend (options: openai, foundry, julep, ollama, huggingface, none)
RAG_BACKEND=openai
```

---

## 2. Provider Configurations

### Julep AI Configuration

To run agents using Julep AI multi-agent platform:

```env
# Select Julep as provider
AGENT_PROVIDER=julep
RAG_BACKEND=julep

# Julep Credentials & Models
JULEP_API_KEY=your-julep-api-key
JULEP_MODEL=claude-3.5-sonnet
JULEP_ENVIRONMENT=production
```

- **`JULEP_API_KEY`**: Your secret Julep API key.
- **`JULEP_MODEL`**: Target LLM model used by Julep workflows (Default: `claude-3.5-sonnet`).
- **`JULEP_ENVIRONMENT`**: Environment mode (Default: `production`).

---

### OpenAI Configuration

To run agents directly via OpenAI's official API:

```env
# Select OpenAI as provider
AGENT_PROVIDER=openai
RAG_BACKEND=openai

# OpenAI Credentials & Models
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Optional custom base URL (for OpenAI-compatible proxies)
# OPENAI_BASE_URL=https://api.openai.com/v1
```

- **`OPENAI_API_KEY`**: Your secret OpenAI API key.
- **`OPENAI_MODEL`**: LLM used for agent classification, summarization, and RAG (Default: `gpt-4o-mini`).
- **`OPENAI_EMBEDDING_MODEL`**: Model used for vector embeddings in RAG (Default: `text-embedding-3-small`).
- **`OPENAI_BASE_URL`**: Custom base URL if using an OpenAI proxy or alternative endpoint.

---

### Azure Microsoft Foundry Configuration

Microsoft Foundry provides OpenAI-compatible Azure endpoints. When using Foundry, supply the `FOUNDRY_*` variables. The system will map these to the underlying OpenAI provider automatically.

```env
# Select OpenAI as provider
AGENT_PROVIDER=openai
RAG_BACKEND=foundry

# Azure Foundry Credentials & Endpoint
FOUNDRY_API_KEY=your-azure-foundry-api-key
FOUNDRY_BASE_URL=https://<your-resource-name>.openai.azure.com/openai/v1/
FOUNDRY_MODEL=your-deployment-name
FOUNDRY_EMBEDDING_MODEL=text-embedding-3-small
```

- **`FOUNDRY_API_KEY`**: Your Azure OpenAI / Foundry resource key.
- **`FOUNDRY_BASE_URL`**: Resource endpoint URL (e.g., `https://distillnews.openai.azure.com/openai/v1/`).
- **`FOUNDRY_MODEL`**: Name of your deployed model in Azure Foundry.
- **`FOUNDRY_EMBEDDING_MODEL`**: Name of your embedding deployment in Azure Foundry.

---

### Local Ollama Configuration

For local offline development using open-source models hosted via Ollama:

```env
# Select Ollama as provider
AGENT_PROVIDER=ollama
RAG_BACKEND=ollama

# Ollama Settings
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

- **`OLLAMA_BASE_URL`**: Address of your running Ollama server instance (Default: `http://localhost:11434`).
- **`OLLAMA_MODEL`**: Local LLM model name (Default: `llama3`).
- **`OLLAMA_EMBEDDING_MODEL`**: Model used for local embeddings (Default: `nomic-embed-text`).

---

### HuggingFace Configuration

To use HuggingFace Inference API or hosted models:

```env
# Select HuggingFace as provider
AGENT_PROVIDER=huggingface
RAG_BACKEND=huggingface

# HuggingFace Credentials & Models
HUGGINGFACE_API_KEY=your-huggingface-token
HUGGINGFACE_MODEL=meta-llama/Llama-3.2-3B-Instruct
HUGGINGFACE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

- **`HUGGINGFACE_API_KEY`** (or **`HF_TOKEN`**): Your HuggingFace User Access Token.
- **`HUGGINGFACE_MODEL`**: Target repository/model identifier (Default: `meta-llama/Llama-3.2-3B-Instruct`).
- **`HUGGINGFACE_EMBEDDING_MODEL`**: Sentence transformer model for embeddings (Default: `sentence-transformers/all-MiniLM-L6-v2`).

---

## 3. Global Overrides & Other System Configurations

### Global Model Override
If `AGENT_MODEL` is defined, it takes precedence over provider-specific model settings (`JULEP_MODEL`, `FOUNDRY_MODEL`, `OPENAI_MODEL`).

```env
AGENT_MODEL=gpt-4o
```

---

### News Source API Keys
To fetch real-time news data across different providers and social platforms, configure the corresponding API keys:

```env
# External News APIs
GNEWS_API_KEY=your-gnews-key
MEDIASTACK_API_KEY=your-mediastack-key
NEWS_API_KEY=your-newsapi-key
RAPIDAPI_KEY=your-rapidapi-key
CORE_API_KEY=your-core-api-key

# Reddit Community Source API
REDDIT_CLIENT_ID=your-reddit-client-id
REDDIT_SECRET=your-reddit-client-secret
```

---

### Database & Authentication Settings

```env
# Database Connection URL
DB_URL=postgresql://user:password@localhost:5432/distillnews

# JWT Secret Key for Session Authentication
JWT_SECRET=your-super-secret-jwt-key
```

---

## 4. Example Complete `.env` File

Below is a complete reference example for a setup using Microsoft Foundry for agent processing and OpenAI for RAG search:

```env
# Provider Selection
AGENT_PROVIDER=openai
RAG_BACKEND=openai

# Azure Foundry Credentials
FOUNDRY_API_KEY=my-azure-key-12345
FOUNDRY_BASE_URL=https://distillnews.openai.azure.com/openai/v1/
FOUNDRY_MODEL=gpt-4o-mini
FOUNDRY_EMBEDDING_MODEL=text-embedding-3-small

# News APIs
GNEWS_API_KEY=your-gnews-api-key
RAPIDAPI_KEY=your-rapidapi-key
REDDIT_CLIENT_ID=your-reddit-id
REDDIT_SECRET=your-reddit-secret

# Server & DB
DB_URL=sqlite:///./distillnews.db
JWT_SECRET=development-secret-key-change-in-prod
```
