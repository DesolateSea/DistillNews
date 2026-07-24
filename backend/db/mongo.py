"""MongoDB connection lifecycle manager."""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import config


class MongoHandle:
    """Single shared MongoDB connection pool for the entire application."""
    _client: AsyncIOMotorClient | None = None
    _db: AsyncIOMotorDatabase | None = None

    @classmethod
    def connect(cls, url: str | None = None, db_name: str = "news_db"):
        url = url or config.DB_URL
        cls._client = AsyncIOMotorClient(url)
        cls._db = cls._client[db_name]

    @classmethod
    def disconnect(cls):
        if cls._client:
            cls._client.close()
            cls._client = None
            cls._db = None

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        if cls._db is None:
            raise RuntimeError("MongoHandle.connect() has not been called")
        return cls._db

    @classmethod
    def collection(cls, name: str):
        return cls.get_db()[name]
