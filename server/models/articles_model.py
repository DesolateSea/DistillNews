from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime


class SourceModel(BaseModel):
    title: str
    url: Optional[HttpUrl] = None
    created_utc: Optional[float] = None
    subreddit: Optional[str] = None
    media: Optional[List[HttpUrl]] = None
    content: Optional[str] = None



class ArticleModel(BaseModel):
    title: str
    summary: Optional[str] = Field(None, alias="description")
    content: Optional[str]
    markdown_content: Optional[str]
    publication_date: datetime = Field(..., alias="publishedAt")
    category: str
    tags: List[str]
    location: Optional[str]
    popularity: int
    duration: Optional[float]
    source: SourceModel


class ArticleInDB(ArticleModel):
    id: Optional[str] = Field(default=None, alias="_id")
class DurationRequest(BaseModel):
    durationMs: float
# Pagination wrapper
class PaginatedArticlesResponse(BaseModel):
    page: int
    limit: int
    has_more: bool
    total: Optional[int]
    feeds: List[ArticleInDB]
class ChatMessage(BaseModel):
    message: str