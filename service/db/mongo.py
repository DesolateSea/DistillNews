"""MongoDB connection lifecycle manager."""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import config

try:
    from service.logger import log
except ImportError:
    log = None


class MongoHandle:
    """Single shared MongoDB connection pool for the entire application."""

    _client: AsyncIOMotorClient | None = None
    _db: AsyncIOMotorDatabase | None = None

    @classmethod
    def connect(cls, url: str | None = None, db_name: str = "news_db"):
        url = url or config.DB_URL
        cls._client = AsyncIOMotorClient(url)
        cls._db = cls._client[db_name]
        if log:
            log.db("MongoDB Connected", f"db={db_name}")

    @classmethod
    def disconnect(cls):
        if cls._client:
            cls._client.close()
            cls._client = None
            cls._db = None
            if log:
                log.db("MongoDB Disconnected")

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        if cls._db is None:
            raise RuntimeError("MongoHandle.connect() has not been called")
        return cls._db

    @classmethod
    def collection(cls, name: str):
        return cls.get_db()[name]

    @classmethod
    async def create_indexes(cls):
        """Create database indexes for user collection."""
        if cls._db is None:
            return
        try:
            users_col = cls.collection("SNAPUsers")
            await users_col.create_index("email", unique=True)
            if log:
                log.db("MongoDB Indexes Created", "SNAPUsers indexed successfully")
        except Exception as e:
            if log:
                log.warn(f"Failed to create MongoDB indexes: {e}")

