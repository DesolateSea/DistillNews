import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from server.routes import auth_routes, user_routes, feed_routes, chat_routes, weather_routes
from server.services.article_service import get_all_articles
from service.db.mongo import MongoHandle
from service.db.redis import RedisHandle
from service.articles import prime_redis_indexes
from service.logger import log
from server.middleware import BodyLimitMiddleware
from server.security import jwt_secret
from server.auth import allowed_origins


@asynccontextmanager
async def lifespan(app: FastAPI):
    jwt_secret()
    if "*" in allowed_origins():
        raise RuntimeError("CORS_ORIGINS must list trusted origins, not '*'")
    MongoHandle.connect()
    await RedisHandle.connect()
    await MongoHandle.create_indexes()
    await prime_redis_indexes()
    try:
        await get_all_articles(current_user=None)
    except Exception:
        pass
    yield
    MongoHandle.disconnect()
    await RedisHandle.disconnect()


app = FastAPI(lifespan=lifespan)

origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(BodyLimitMiddleware)

app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(feed_routes.router)
app.include_router(chat_routes.router)
app.include_router(weather_routes.router)


@app.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "ok"}
