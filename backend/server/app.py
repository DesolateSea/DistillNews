import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.routes import auth_routes, user_routes, feed_routes, chat_routes, weather_routes
from server.services.article_service import start_scheduler, shutdown_scheduler, store_article
from contextlib import asynccontextmanager
from db.mongo import MongoHandle
from db.redis import RedisHandle
from utils.logger import log


@asynccontextmanager
async def lifespan(app: FastAPI):
    MongoHandle.connect()
    await RedisHandle.connect()
    try:
        log.info("Storing all new articles")
        await store_article()
        log.success("Stored all new articles")
        start_scheduler()
    except Exception as e:
        log.warn(f"Startup tasks failed ({e}). Running without scheduler.")
    yield
    try:
        shutdown_scheduler()
    except Exception:
        pass
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

app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(feed_routes.router)
app.include_router(chat_routes.router)
app.include_router(weather_routes.router)


@app.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "ok"}