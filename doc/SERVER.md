# Server

The FastAPI server in `server/` exposes the product API, owns application data, and coordinates scheduled publication of processed articles. Its entry point is `server/app.py`.

## Contents

- [Database Layer (`service/db/`)](#database-layer-servicedb)
- [Responsibilities and Data Ownership](#responsibilities-and-data-ownership)
- [Local Setup](#local-setup)
- [Configuration](#configuration)
- [Routes](#routes)
- [Container Deployment](#container-deployment)

---

## Database Layer (`service/db/`)

The server interacts with all application data through unified database and storage handles:

- **`ArticleStore`** (`service/db/article_store.py`): Pluggable article storage interface created via `create_article_store()`. Backed by `AzureBlobArticleStore` (`service/db/azure_blob_store.py`) when `ARTICLE_STORE_BACKEND=azure` or `FileArticleStore` (`service/db/filestore.py`) when `ARTICLE_STORE_BACKEND=file`.
- **`MongoHandle`** (`service/db/mongo.py`): Manages the `AsyncIOMotorClient` pool for user accounts (`news_db.SNAPUsers`) and interaction weights.
- **`RedisHandle`** (`service/db/redis.py`): Manages async Redis connections for short-lived email OTP verification sessions.
- **`FileStore`** (`service/db/filestore.py`): Manages low-level raw file I/O for raw scrapes and API response fixtures.

---

## Responsibilities and Data Ownership

- **ArticleStore** owns article loading and retrieval. The server loads feeds directly from the active `ArticleStore` (`azure` blob container or local `file` store), with automatic fallback if MongoDB is offline or unpopulated.
- **MongoDB** stores user profiles, preferences, and interaction bias scores in `news_db.SNAPUsers`.
- **Redis** handles email OTP validation tokens with expiration timeouts.
- The server proxies OpenWeather geocoding so its API key is never sent to the browser.
- The Node service in `server/email/` delivers OTP and newsletter emails via Nodemailer.

MongoDB is the user product database; it is not the RAG vector store. Semantic retrieval is owned by the `service/chatbot/` package and is documented in [RAG_CHATBOT.md](RAG_CHATBOT.md). The pipeline owns how processed JSON files are created; see [AGENT_PIPELINE.md](AGENT_PIPELINE.md).

---

## Local Setup

```bash
uvicorn server.app:app --reload --port 8000
```

---

## Configuration

Server settings are loaded via `config.py` from `.env` organized into structured sections:

| Key | Section | Description | Default / Example |
|:---|:---|:---|:---|
| `PORT` | Backend Runtime | FastAPI HTTP port | `8000` |
| `DB_URL` | User Database | MongoDB connection URI | `mongodb://mongo:27017/evolution` |
| `REDIS_URL` | User Database | Redis connection URI | `redis://redis:6379/0` |
| `ARTICLE_STORE_BACKEND` | Article Store | Article storage backend (`azure` or `file`) | `azure` |
| `AZURE_STORAGE_CONNECTION_STRING` | Article Store | Azure Blob Storage connection string | *(required for azure)* |
| `AZURE_BLOB_CONTAINER` | Article Store | Azure blob container name | `processed-articles` |
| `JWT_SECRET` | Backend Runtime | Secret key for JWT signing | *(required)* |
| `CORS_ORIGINS` | Backend Runtime | Allowed CORS origin URLs | `http://localhost:3000` |
| `OPENWEATHER_API_KEY` | Pipeline / Data | Key for weather proxy & data | *(optional)* |
| `EMAIL` | Email Service | Sender Gmail address for OTPs | *(optional)* |
| `PASS` | Email Service | Sender Gmail app password | *(optional)* |

---

## Routes

| Method | Endpoint | Description | Auth Required |
|:---|:---|:---|:---:|
| `POST` | `/api/v1/auth/register` | Register new user account | No |
| `POST` | `/api/v1/auth/login` | Login & receive JWT token | No |
| `POST` | `/api/v1/auth/send-otp` | Trigger OTP email verification | No |
| `POST` | `/api/v1/auth/verify-otp` | Verify OTP token & sign in | No |
| `GET` | `/api/v1/user/preferences` | Get user category preferences | Yes |
| `POST` | `/api/v1/user/preferences` | Update category preferences | Yes |
| `GET` | `/api/v1/feed` | Personalized article feed | Optional |
| `GET` | `/api/v1/feed/pagination` | Paginated article feed | Optional |
| `GET` | `/api/v1/feed/{article_id}` | Read single article (increments popularity) | Optional |
| `POST` | `/api/v1/feed/{article_id}/duration` | Track user dwell time & update bias weights | Optional |
| `POST` | `/api/v1/chat` | Send conversational query to RAG chatbot | Optional |
| `GET` | `/api/v1/weather` | Geocoded weather proxy | No |
| `GET` | `/health` | Liveness health check | No |

---

## Container Deployment

Build and run standalone:

```bash
docker build -f Dockerfile.backend -t distillnews-backend .
docker run -p 8000:8000 --env-file .env distillnews-backend
```
