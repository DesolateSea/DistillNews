"""
Stream abstraction and data envelope primitives.

Provides:
  - Stream: Abstract base class for bounded, thread-safe item flows.
  - QueueStream: Concrete in-memory stream backed by a queue.Queue.
  - StreamItem: Marker base class for stream payloads.
  - RawArticle: Standard data envelope yielded by scrapers & APIs.
  - is_stream_type: Helper to check if a type annotation is a stream type.
"""

from __future__ import annotations

import inspect
import queue
import threading
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, Iterator, TypeVar

T = TypeVar("T")


class StreamItem:
    """Marker base class for typed payloads moving through a Stream."""
    pass


@dataclass
class RawArticle(StreamItem):
    """
    Standardized envelope for raw content yielded by any producer.

    Scrapers, RSS readers, and API fetchers emit instances of this
    into the pipeline, allowing downstream stages (e.g. ``parse``) to
    consume from any source uniformly.
    """

    source: str                          # e.g. "reddit", "gnews", "scrape"
    payload: Any                         # raw dict, HTML string, or API response
    url: str = ""
    article_id: str = ""                 # optional pre-computed ID
    title: str = ""
    publication_date: str | int = ""

    def get_title(self) -> str:
        if self.title:
            return self.title
        if isinstance(self.payload, dict):
            return str(self.payload.get("title", ""))
        return ""

    def get_publication_date(self) -> str | int:
        if self.publication_date:
            return self.publication_date
        if isinstance(self.payload, dict):
            return self.payload.get("publishedAt") or self.payload.get("published_date") or self.payload.get("created_utc") or ""
        return ""


class Stream(ABC, Generic[T]):
    """
    Abstract stream channel connecting producers and consumers.

    Provides bounded buffering, thread-safe emit/consume, and lifecycle tracking.
    """

    def __init__(self, name: str, maxsize: int = 128) -> None:
        self.name = name
        self.maxsize = maxsize
        self._closed = False
        self._lock = threading.Lock()
        self.stats: dict[str, int] = {"emitted": 0, "consumed": 0}

    @abstractmethod
    def emit(self, item: T, timeout: float | None = None) -> None:
        """Push an item into the stream. Blocks if buffer is full."""
        pass

    @abstractmethod
    def get(self, block: bool = True, timeout: float | None = None) -> T:
        """Retrieve an item from the stream."""
        pass

    @abstractmethod
    def qsize(self) -> int:
        """Return current number of buffered items."""
        pass

    def close(self) -> None:
        """Signal that no more items will be emitted."""
        with self._lock:
            self._closed = True

    @property
    def is_closed(self) -> bool:
        with self._lock:
            return self._closed

    def __iter__(self) -> Iterator[T]:
        while True:
            try:
                yield self.get(timeout=0.05)
            except queue.Empty:
                if self.is_closed:
                    break


class QueueStream(Stream[T]):
    """In-memory thread-safe queue implementation of Stream."""

    def __init__(self, name: str, maxsize: int = 128) -> None:
        super().__init__(name=name, maxsize=maxsize)
        self._queue: queue.Queue[T] = queue.Queue(maxsize=maxsize)

    def emit(self, item: T, timeout: float | None = None) -> None:
        if self.is_closed:
            raise RuntimeError(f"Cannot emit to closed stream {self.name!r}")
        self._queue.put(item, timeout=timeout)
        with self._lock:
            self.stats["emitted"] += 1

    def get(self, block: bool = True, timeout: float | None = None) -> T:
        item = self._queue.get(block=block, timeout=timeout)
        with self._lock:
            self.stats["consumed"] += 1
        return item

    def qsize(self) -> int:
        return self._queue.qsize()


KNOWN_STREAM_NAMES = frozenset({"RawArticle", "Stream", "StreamItem", "QueueStream"})


def is_stream_type(annotation: Any) -> bool:
    """
    Check whether a type annotation represents a Stream or StreamItem.

    Used by ``@stage`` to determine whether a parameter should be
    stream-injected (if True) or matched by function name (if False).
    Supports runtime types and deferred string annotations (PEP 563).
    """
    if annotation is inspect.Parameter.empty:
        return False

    # String annotation (e.g. from `from __future__ import annotations`)
    if isinstance(annotation, str):
        clean = annotation.strip().strip("'\"")
        base = clean.split("[")[0].split(".")[-1]
        if base in KNOWN_STREAM_NAMES:
            return True
        if clean.startswith("Stream[") or clean.startswith("QueueStream["):
            return True
        return False

    # Direct class check
    if isinstance(annotation, type):
        if issubclass(annotation, (Stream, StreamItem)):
            return True
        if annotation is RawArticle:
            return True

    # Generic check like Stream[RawArticle]
    origin = typing.get_origin(annotation)
    if origin is not None and isinstance(origin, type) and issubclass(origin, Stream):
        return True

    return False
