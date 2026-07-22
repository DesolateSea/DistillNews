from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.routes import auth_routes, user_routes, feed_routes, chat_routes
from apps.services.article_service import start_scheduler, shutdown_scheduler, store_article
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        print("Storing all new articles")
        await store_article()
        print("Stored all new articles")
        start_scheduler()
    except Exception as e:
        print(f"Warning: startup tasks failed ({e}). Server will run without scheduled article ingestion.")
    yield
    try:
        shutdown_scheduler()
    except Exception:
        pass

app = FastAPI(lifespan=lifespan)

origins = ["*"]
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