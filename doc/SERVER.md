# FastAPI Web Server Architecture

The web server tier in `server/` exposes the REST API, manages authentication, proxies third-party services, and serves article feeds. Its entrypoint is `server/app.py`.

---

## Data Layer & Persistence (`service/db/`)

- **`ArticleStore`** (`service/db/article_store.py`): Pluggable article repository. Supports `AzureBlobArticleStore` (`ARTICLE_STORE_BACKEND=azure`) or `FileArticleStore` (`ARTICLE_STORE_BACKEND=file`).
- **`MongoHandle`** (`service/db/mongo.py`): MongoDB pool for user accounts (`news_db.SNAPUsers`) and interaction bias weights.
- **`RedisHandle`** (`service/db/redis.py`): Redis connection handle for OTP tokens and session caching.

---

## API Routes Overview

| Route | Endpoint | Method | Description | Auth |
|:---|:---|:---:|:---|:---:|
| `Auth` | `/api/v1/auth/register` | `POST` | User registration | No |
| `Auth` | `/api/v1/auth/login` | `POST` | User login & JWT issuance | No |
| `Auth` | `/api/v1/auth/send-otp` | `POST` | Dispatch email OTP code | No |
| `Auth` | `/api/v1/auth/verify-otp` | `POST` | Verify OTP code & return token | No |
| `User` | `/api/v1/user/preferences` | `GET` | Retrieve category preferences | Yes |
| `User` | `/api/v1/user/preferences` | `POST` | Save category preferences | Yes |
| `Feed` | `/feeds/{page}/{limit}` | `GET` | Feed retrieval with optional category filtering | Optional |
| `Feed` | `/feeds/article/{id}` | `GET` | Retrieve single article by ID | Optional |
| `Chat` | `/api/v1/chat` | `POST` | Send query to RAG chatbot assistant | Optional |
| `Weather`| `/api/v1/weather` | `GET` | OpenWeather proxy endpoint | No |
| `Health` | `/health` | `GET` | Server liveness check | No |

---

## Weather & Third-Party Proxying

The server proxies OpenWeather geocoding and weather API calls so third-party secrets remain secure on the server and are never exposed in client browser bundles.

---

## Development & Production Commands

```bash
# Local development with auto-reload
uvicorn server.app:app --reload --port 8000

# Docker container build
docker build -f Dockerfile.backend -t distillnews-backend .
```
