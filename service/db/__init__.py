"""Database connection and repository handles layer."""

from .mongo import MongoHandle
from .redis import RedisHandle

# Re-export blob and article storage abstractions for backward compatibility
from service.blob import (
    ArticleStore,
    create_article_store,
    FileStore,
    FileArticleStore,
    AzureBlobArticleStore,
)

__all__ = [
    "MongoHandle",
    "RedisHandle",
    "ArticleStore",
    "create_article_store",
    "FileStore",
    "FileArticleStore",
    "AzureBlobArticleStore",
]
