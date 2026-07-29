import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.routes import auth_routes, user_routes, feed_routes, chat_routes, weather_routes
from service.db.mongo import MongoHandle
from service.db.redis import RedisHandle
from service.logger import log


@asynccontextmanager
async def lifespan(app: FastAPI):
    MongoHandle.connect()
    await RedisHandle.connect()
    await MongoHandle.create_indexes()
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

app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(feed_routes.router)
app.include_router(chat_routes.router)
app.include_router(weather_routes.router)


@app.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "ok"}