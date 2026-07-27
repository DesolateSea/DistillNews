# Server

<<<<<<< HEAD
The FastAPI server in `backend/server/` exposes the product API, owns application data, and coordinates scheduled publication of processed articles. Its entry point is `backend/server/app.py`.

---
=======
The FastAPI server in `server/` exposes the product API, owns application data, and coordinates scheduled publication of processed articles. Its entry point is `server/app.py`.
>>>>>>> 582a92f (refactor: The code base has sperated the pipelines completely from the)

## Contents

- [Database Layer (`service/db/`)](#database-layer-servicedb)
- [Responsibilities and Data Ownership](#responsibilities-and-data-ownership)
- [Local Setup](#local-setup)
- [Configuration](#configuration)
- [Routes](#routes)
- [Container Deployment](#container-deployment)

<<<<<<< HEAD
---

## Database Layer (`db/`)

The server interacts with all application data through unified database and storage handles:

- **`MongoHandle`** (`db/mongo.py`): Manages the `AsyncIOMotorClient` pool for product collections (`news_db.articles` and `news_db.SNAPUsers`).
- **`RedisHandle`** (`db/redis.py`): Manages async Redis connections for short-lived email OTP verification sessions.
- **`FileStore`** (`db/storage.py`): Manages disk file storage, JSON reading/writing, automatic `created_at` UTC timestamping, deduplication checks, and article list iteration.

---
=======
## Database Layer (`service/db/`)

The server interacts with all application data through unified database and storage handles:

- **`MongoHandle`** (`service/db/mongo.py`): Manages the `AsyncIOMotorClient` pool for product collections (`news_db.articles` and `news_db.SNAPUsers`).
- **`RedisHandle`** (`service/db/redis.py`): Manages async Redis connections for short-lived email OTP verification sessions.
- **`FileStore`** (`service/db/storage.py`): Manages file storage, JSON reading/writing, deduplication checks, and article list iteration.
>>>>>>> 582a92f (refactor: The code base has sperated the pipelines completely from the)

## Responsibilities and Data Ownership

- **MongoDB** stores normalized articles in `news_db.articles` and user preferences/interaction scores in `news_db.SNAPUsers`.
- **Redis** handles email OTP validation tokens with expiration timeouts.
- **FileStore** handles loading processed article JSON files on server startup via `FileStore.list_processed_files()` into MongoDB, then schedules recurring sync jobs every 24 hours.
- The server proxies OpenWeather geocoding so its API key is never sent to the browser.
- The Node service in `server/email/` delivers OTP and newsletter emails via Nodemailer.

MongoDB is the news product database; it is not the RAG vector store. Semantic retrieval is owned by the `service/chatbot/` package and is documented in [RAG_CHATBOT.md](RAG_CHATBOT.md). The pipeline owns how processed JSON files are created; see [AGENT_PIPELINE.md](AGENT_PIPELINE.md).

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
| `DB_URL` | Backend Runtime | MongoDB connection URI | `mongodb://mongo:27017/evolution` |
| `REDIS_URL` | Backend Runtime | Redis connection URI | `redis://redis:6379/0` |
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
