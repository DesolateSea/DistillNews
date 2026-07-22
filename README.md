<h1 align="center">Distill News : AI-Powered Community News Website</h1>
<p align="center">
</p>

<a href="https://hack36.in"> <img src="https://postimage.me/images/2025/04/19/built-at-hack36.png" height=24px> </a>

### Hack36 Theme : Community and Upliftment

### Applicable Tracks : Julep AI

## Introduction

Distill News is an automated news website made using multi-agents with the simple goal in mind - to surf the internet and find every possible news.

### The Problem 
News articles written by media channels can not cover everything due to a bias towards profit and limited workforce. 

While the internet is packed with all sorts of news all over the place on different platforms with no unified platform where one can find all the news, something might be posted on Reddit or X, it is impossible to follow the fast-paced nature of the internet.

This is where our goal comes in - using AI agents to find news from data all over the web from news articles to community posts and present them in a structured, personalized, and timely manner for engagement.

### Our Solution 
An AI-driven platform that cuts through the noise, bias, and bloat of traditional media by extracting core news from web scraping, trusted APIs, and real-time community sources like Reddit. 

The system strips clickbait and filler content found in news articles, and as well as rewrites news and community posts into clear, professional-grade articles using Julep AI.

By combining structured extraction (via Julep AI), community-driven discovery, and smart personalization, we empower communities with direct access to reliable local and global updates—without clickbait, corporate spin, or media gatekeeping. 

This approach also enables underrepresented voices on social platforms to reach a wider audience through well-written, structured articles.

### Key Features:

**AI-Generated News Feed:** Aggregates content from APIs (GNews, MediaStack, RapidAPI) and community platforms like Reddit.

**Noise Filtering:** Removes clickbait, ads, duplicates, and irrelevant content automatically.

**Multi-Agent Article Processing (via Julep AI):**

Classifies input data as news or not. Extracts structured content (title, summary, date, location). Formats it into clean, professional markdown

**Personalized Feed:** Learns from your reading time and interests. Dynamically adapts story selection using topic-weighted preferences

**RAG-based AI Assistant:** Includes article context automatically. Supports session memory for follow-ups. Handles both local and global queries conversationally.

**Clean UI**: Minimalist, responsive interface with login and onboarding flow.

### Demo Video Link:
  <a href="https://youtu.be/DAjnclylWJI?si=9GWWL3lOncghZvmW">Demo link</a>
  
### Presentation Link:
  <a href="https://www.canva.com/design/DAGlJFoPnyo/65fJrZEw6t2cch7ZaEOyfQ/edit?utm_content=DAGlJFoPnyo&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton"> PPT link here </a>

## Technology Stack:
1) Julep AI
2) Next.js
3) FastAPI
4) BeautifulSoup
5) nodemailer (javascript)

## Languages used:
- Python
- Typescript
- Javascrip
- YAML
  
## Idea

We want to build an AI-driven platform to:

- **Aggregate** core news from web scraping, trusted APIs, and community sources.
- **Filter** out filler content, ads, and fluff.
- **Rewrite** articles and community posts into concise, professional-grade news.
- **Personalize** delivery based on interests, reading behavior, and location.

## Wow Factors 🌟

1. **Concise Rewriting**
   - Removes filler, ads, and fluff.
   - Rewrites content for clarity and brevity.

2. **Reddit & Local Feeds**
   - Surfaces hyperlocal stories directly from community posts and public forums.

3. **AI-Enhanced Writing**
   - Converts raw user-generated content into professional-quality news articles using Julep AI.

4. **Personalized Recommendations**
   - Delivers news based on user interests, reading behavior, and location.

5. **Curated Newsletters**
   - Sends daily or weekly digests tailored to each subscriber.

6. **Print-Style Digital Newspaper**
   - Offers a traditional-style newspaper layout with various sections as an alternative to typical email newsletters.

7. **Human Validation (Optional)**
   - Allows moderators or volunteers to fact-check and approve stories when needed.

---

*Built with Julep AI and open-source community data.*

## Installation / Quickstart
```bash
cd frontend
npm install
```

```bash
pip install -r requirements.txt
fastapi dev server/app.py
```

```bash
cd frontend
npm run dev
```

Make sure to add `.env` file and API keys

### Microsoft Foundry setup

The OpenAI provider supports Microsoft Foundry's OpenAI-compatible endpoint
with an API key. Copy `.env.example` to `.env`, then replace the placeholders
with the Foundry API key and the model deployment name from your resource:

```env
AGENT_PROVIDER=openai
FOUNDRY_API_KEY=your-foundry-api-key
FOUNDRY_BASE_URL=https://your-resource.openai.azure.com/openai/v1/
FOUNDRY_MODEL=your-model-deployment-name
```

`FOUNDRY_BASE_URL` may also be the resource URL without `/openai/v1`; the
provider adds that path automatically. Keep `.env` private and do not commit
the API key.

## Contributors:

Team Name: SNAP_back_to_reality

- [Shivam Aryan](https://github.com/Aryan10)
- [Nishant Mohan](https://github.com/Nishant040305)
- [Poojan Kothari](https://github.com/techguy940)
- [Shaurya Singh](https://github.com/shauryasf)

### Made at:
<a href="https://hack36.in"> <img src="https://postimage.me/images/2025/04/19/built-at-hack36.png" height=24px> </a>
