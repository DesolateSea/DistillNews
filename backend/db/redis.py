"""Redis connection lifecycle manager."""
from redis.asyncio import Redis
from config import config


class RedisHandle:
    """Single shared Redis connection for the entire application."""
    _client: Redis | None = None

    @classmethod
    async def connect(cls, url: str | None = None):
        cls._client = Redis.from_url(
            url or config.REDIS_URL, decode_responses=True
        )

    @classmethod
    async def disconnect(cls):
        if cls._client:
            await cls._client.close()
            cls._client = None

    @classmethod
    def client(cls) -> Redis:
        if cls._client is None:
            raise RuntimeError("RedisHandle.connect() has not been called")
        return cls._client
