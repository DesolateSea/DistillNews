# Distill News : AI-Powered Community News Website

Distill News is an automated news aggregation and synthesis platform powered by AI multi-agents. Its goal is to crawl, aggregate, filter, and summarize news across the internet—ranging from mainstream news APIs to public community forums—presenting content in a clean, structured, and personalized format.

## Introduction

### The Problem
Traditional news outlets often fail to cover everything due to profit motives, regional biases, and limited workforce resources. Meanwhile, public forums and social platforms like Reddit or X overflow with real-time updates and grassroots stories, but lack a unified, noise-free platform for reader consumption.

### The Solution
Distill News uses AI agents to extract core news from web scraping, trusted APIs, and real-time community sources. The platform strips away clickbait, ads, and filler, rewriting posts into concise, professional-grade news articles.

By combining structured AI extraction, community discovery, and smart personalization, Distill News provides direct access to reliable local and global updates—without clickbait, corporate spin, or media gatekeeping.

### Demo Video
🎬 [Watch Demo Video](https://youtu.be/DAjnclylWJI?si=9GWWL3lOncghZvmW)

---

## Key Features

- **AI-Generated News Feed:** Aggregates content from news APIs (GNews, MediaStack, RapidAPI) and community platforms like Reddit.
- **Noise & Fluff Filtering:** Automatically removes clickbait, advertisements, duplicates, and filler content.
- **Multi-Agent Processing:** Classifies incoming data, extracts key metadata (title, summary, date, location), and formats news into clean markdown.
- **Personalized Recommendations:** Learns from user reading time and interests, adapting story selection dynamically using topic-weighted preferences.
- **RAG-based AI Assistant:** Includes context from articles, supports session memory for follow-up questions, and handles both local and global news queries conversationally.
- **Newsletter & Newspaper Views:** Generates curated email digests and a digital print-style newspaper layout.
- **Clean UI:** Responsive, modern interface with streamlined user onboarding.

---

## Technology Stack

- **Frontend:** Next.js, React, TypeScript, Tailwind CSS
- **Backend:** FastAPI, Python
- **AI & Multi-Agents:** Julep AI / OpenAI / Microsoft Foundry
- **Scraping & Processing:** BeautifulSoup, HTTPX
- **Services:** Nodemailer

### Docker deployment

The backend and its MongoDB dependency can be run with the full stack from the
repository root:

```bash
cp .env.example .env
# Add the required API keys, JWT_SECRET, and database settings to .env.
docker compose up --build
```

The frontend is available at `http://localhost:3000` and the backend at
`http://localhost:8000`. The backend container runs as a non-root user, waits
for MongoDB to become healthy, exposes `/health` for container health checks,
and persists MongoDB data in the `mongo-data` volume.

For production, set `NEXT_PUBLIC_API_URL` to the public backend URL and
`CORS_ORIGINS` to the public frontend URL before building. Do not commit `.env`
or any API keys.

---

## Getting Started

### Prerequisites
- Python 3.9+
- Node.js 18+ & npm

### Installation & Local Setup

1. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

2. **Backend Setup**
   ```bash
   pip install -r requirements.txt
   fastapi dev server/app.py
   ```

### Environment Configuration

Copy `.env.example` to `.env` in the project root and add your API keys:

```env
AGENT_PROVIDER=openai
FOUNDRY_API_KEY=your-foundry-api-key
FOUNDRY_BASE_URL=https://your-resource.openai.azure.com/openai/v1/
FOUNDRY_MODEL=your-model-deployment-name
```

For detailed agent setup instructions (including **Julep AI**, **OpenAI**, **Azure Microsoft Foundry**, **Ollama**, and **HuggingFace**), refer to [doc/SETUP.md](doc/SETUP.md).

---

## Team & Acknowledgements

### Contributors
**Team:** `SNAP_back_to_reality`

- [Shivam Aryan](https://github.com/Aryan10)
- [Nishant Mohan](https://github.com/Nishant040305)
- [Poojan Kothari](https://github.com/techguy940)
- [Shaurya Singh](https://github.com/shauryasf)

### Built At
Originally created during **Hack36**.

<a href="https://hack36.in">
  <img src="https://postimage.me/images/2025/04/19/built-at-hack36.png" height="24px" alt="Built at Hack36">
</a>

