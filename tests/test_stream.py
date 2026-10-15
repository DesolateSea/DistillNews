"""
Tests for stream primitives, data envelopes, and M:1 stream ingestion.

Covers:
  - Stream and QueueStream bounded queue, emit, get, iteration, lifecycle
  - RawArticle data envelope and ID derivation
  - @stage stream annotation vs name-to-function matching
  - M:1 fan-in: multiple producers -> single parse stage -> downstream chain
"""

from __future__ import annotations

import queue
import time
import pytest

from pipeline.engine.stream import (
    Stream,
    QueueStream,
    StreamItem,
    RawArticle,
    is_stream_type,
)
from pipeline.engine.stage import (
    stage,
    clear_registered_stages,
    get_registered_stages,
)
from pipeline.engine.registry import StageRegistry
from pipeline.engine.runner import StreamingRunner, _derive_article_id
from pipeline.engine.task import DropArticle, PipelineContext, TaskState


@pytest.fixture(autouse=True)
def _clear():
    clear_registered_stages()
    yield
    clear_registered_stages()


# ═══════════════════════════════════════════════════════════════════
# Stream & QueueStream tests
# ═══════════════════════════════════════════════════════════════════

class TestQueueStream:

    def test_emit_and_get(self):
        s = QueueStream[str](name="test", maxsize=10)
        s.emit("item1")
        s.emit("item2")
        assert s.qsize() == 2
        assert s.get() == "item1"
        assert s.get() == "item2"
        assert s.qsize() == 0
        assert s.stats["emitted"] == 2
        assert s.stats["consumed"] == 2

    def test_close_lifecycle(self):
        s = QueueStream[int](name="nums", maxsize=5)
        assert not s.is_closed
        s.emit(1)
        s.emit(2)
        s.close()
        assert s.is_closed

        # Cannot emit to closed stream
        with pytest.raises(RuntimeError, match="closed stream"):
            s.emit(3)

        # Existing items can still be consumed
        items = list(s)
        assert items == [1, 2]

    def test_is_stream_type_detection(self):
        assert is_stream_type(RawArticle) is True
        assert is_stream_type(StreamItem) is True
        assert is_stream_type(Stream) is True
        assert is_stream_type(QueueStream) is True
        assert is_stream_type(QueueStream[RawArticle]) is True

        # Non-stream types
        assert is_stream_type(int) is False
        assert is_stream_type(str) is False
        assert is_stream_type(dict) is False
        assert is_stream_type(list) is False


# ═══════════════════════════════════════════════════════════════════
# RawArticle Envelope
# ═══════════════════════════════════════════════════════════════════

class TestRawArticle:

    def test_raw_article_attributes(self):
        raw = RawArticle(
            source="reddit",
            payload={"text": "hello"},
            url="https://reddit.com/post/1",
            title="Cool Story",
            publication_date=1700000000,
        )
        assert raw.source == "reddit"
        assert raw.get_title() == "Cool Story"
        assert raw.get_publication_date() == 1700000000
        assert raw.url == "https://reddit.com/post/1"

    def test_raw_article_payload_fallback(self):
        raw = RawArticle(
            source="gnews",
            payload={"title": "From Dict", "publishedAt": "2026-01-01T00:00:00Z"},
        )
        assert raw.get_title() == "From Dict"
        assert raw.get_publication_date() == "2026-01-01T00:00:00Z"

    def test_derive_article_id(self):
        raw = RawArticle(
            source="test",
            payload={},
            title="Tech Breakthrough",
            publication_date="2026-09-12",
        )
        aid1 = _derive_article_id(raw)
        aid2 = _derive_article_id(raw)
        assert aid1 == aid2
        assert len(aid1) == 16


# ═══════════════════════════════════════════════════════════════════
# @stage Annotation vs Pytest Name Matching
# ═══════════════════════════════════════════════════════════════════

class TestStageStreamIntrospection:

    def test_stream_annotated_parameter_injected(self):
        @stage
        def parse(article: RawArticle):
            return article

        defn = parse.__stage__
        assert defn.dependencies == ()  # Not a function-name dependency
        assert len(defn.stream_dependencies) == 1
        assert defn.stream_dependencies[0][0] == "article"
        assert defn.stream_dependencies[0][1] is RawArticle

    def test_unannotated_parameter_is_function_name_dep(self):
        @stage
        def dedup(parse):
            return parse

        defn = dedup.__stage__
        assert defn.dependencies == ("parse",)
        assert defn.stream_dependencies == ()

    def test_non_stream_annotation_is_function_name_dep(self):
        @stage
        def format_content(parse: dict):
            return parse

        defn = format_content.__stage__
        assert defn.dependencies == ("parse",)
        assert defn.stream_dependencies == ()

    def test_mixed_dependencies_and_ctx(self):
        @stage
        def parse_with_ctx(article: RawArticle, ctx):
            return article

        defn = parse_with_ctx.__stage__
        assert defn.dependencies == ()
        assert len(defn.stream_dependencies) == 1
        assert defn.stream_dependencies[0][0] == "article"


# ═══════════════════════════════════════════════════════════════════
# M:1 Fan-in Pipeline Integration
# ═══════════════════════════════════════════════════════════════════

class TestStreamFanInPipeline:

    def test_multi_producer_single_consumer(self):
        """
        Two producers (reddit and gnews) both yield RawArticle.
        A single 'parse' stage consumes from the stream.
        Downstream 'dedup' consumes 'parse' by function name.
        """
        @stage
        def fetch_reddit():
            yield RawArticle(source="reddit", payload={"title": "Reddit Post 1"})
            yield RawArticle(source="reddit", payload={"title": "Reddit Post 2"})

        @stage
        def fetch_gnews():
            yield RawArticle(source="gnews", payload={"title": "GNews Article 1"})

        @stage
        def parse(article: RawArticle) -> dict:
            return {
                "title": article.get_title().upper(),
                "src": article.source,
            }

        @stage
        def dedup(parse) -> str:
            return f"processed:{parse['title']} (from {parse['src']})"

        reg = StageRegistry()
        reg.discover()

        runner = StreamingRunner(registry=reg, max_workers=4)
        runner.run()

        # Check parse tasks (3 articles total from 2 producers)
        parse_tasks = [
            t for t in runner.get_all_tasks()
            if t.stage_name == "parse" and t.state == TaskState.DONE
        ]
        assert len(parse_tasks) == 3

        # Check dedup tasks (3 articles)
        dedup_tasks = [
            t for t in runner.get_all_tasks()
            if t.stage_name == "dedup" and t.state == TaskState.DONE
        ]
        assert len(dedup_tasks) == 3

        results = sorted(t.result for t in dedup_tasks)
        assert results == [
            "processed:GNEWS ARTICLE 1 (from gnews)",
            "processed:REDDIT POST 1 (from reddit)",
            "processed:REDDIT POST 2 (from reddit)",
        ]

    def test_stream_consumer_with_drop_article(self):
        """
        parse stage raises DropArticle for specific items.
        """
        @stage
        def source():
            yield RawArticle(source="web", payload={"title": "keep"})
            yield RawArticle(source="web", payload={"title": "drop_me"})

        @stage
        def parse(article: RawArticle):
            if "drop" in article.get_title():
                raise DropArticle("unwanted")
            return article.get_title()

        @stage
        def finalize(parse):
            return f"final:{parse}"

        reg = StageRegistry()
        reg.discover()

        runner = StreamingRunner(registry=reg, max_workers=2)
        runner.run()

        finalize_tasks = [
            t for t in runner.get_all_tasks()
            if t.stage_name == "finalize" and t.state == TaskState.DONE
        ]
        assert len(finalize_tasks) == 1
        assert finalize_tasks[0].result == "final:keep"

        dropped_tasks = [
            t for t in runner.get_all_tasks()
            if t.state == TaskState.DROPPED and not t.article_id.startswith("__producer__")
        ]
        assert len(dropped_tasks) >= 2  # parse + finalize for drop_me
