"""Redis connection lifecycle manager."""

from redis.asyncio import Redis
from config import config

try:
    from service.logger import log
except ImportError:
    log = None


class RedisHandle:
    """Single shared Redis connection for the entire application."""

    _client: Redis | None = None

    @classmethod
    async def connect(cls, url: str | None = None):
        target_url = url or config.REDIS_URL
        cls._client = Redis.from_url(target_url, decode_responses=True)
        if log:
            log.db("Redis Connected", target_url)

    @classmethod
    async def disconnect(cls):
        if cls._client:
            await cls._client.close()
            cls._client = None
            if log:
                log.db("Redis Disconnected")

    @classmethod
    def client(cls) -> Redis:
        if cls._client is None:
            raise RuntimeError("RedisHandle.connect() has not been called")
        return cls._client
