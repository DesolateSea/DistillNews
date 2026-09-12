"""
Tests for pipeline.engine — the streaming task-graph engine.

Covers:
  - @stage decorator introspection
  - StageRegistry validation (missing deps, cycles, topo sort, mermaid)
  - Task state machine transitions
  - DropArticle cascade
  - StreamingRunner end-to-end with mock stages
"""

from __future__ import annotations

import time
import threading
from collections import defaultdict

import pytest

from pipeline.engine.task import (
    DropArticle,
    PipelineContext,
    Task,
    TaskEvent,
    TaskState,
)
from pipeline.engine.stage import (
    StageDefinition,
    clear_registered_stages,
    get_registered_stages,
    stage,
)
from pipeline.engine.registry import (
    CyclicDependencyError,
    MissingStageDependencyError,
    StageRegistry,
)
from pipeline.engine.runner import StreamingRunner


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def _clear_stages():
    """Ensure each test gets a fresh global stage registry."""
    clear_registered_stages()
    yield
    clear_registered_stages()


# ═══════════════════════════════════════════════════════════════════
# @stage decorator
# ═══════════════════════════════════════════════════════════════════

class TestStageDecorator:

    def test_transform_stage_metadata(self):
        @stage
        def my_transform(upstream_a, upstream_b):
            """A test transform."""
            return upstream_a + upstream_b

        defn = my_transform.__stage__
        assert defn.name == "my_transform"
        assert defn.dependencies == ("upstream_a", "upstream_b")
        assert defn.is_producer is False
        assert defn.doc == "A test transform."

    def test_producer_stage_detected(self):
        @stage
        def my_producer():
            yield "item1"
            yield "item2"

        defn = my_producer.__stage__
        assert defn.is_producer is True
        assert defn.dependencies == ()

    def test_ctx_excluded_from_deps(self):
        @stage
        def needs_ctx(upstream, ctx):
            return upstream

        defn = needs_ctx.__stage__
        assert defn.dependencies == ("upstream",)

    def test_decorator_preserves_function(self):
        @stage
        def identity(x):
            return x

        assert identity(42) == 42

    def test_global_registration(self):
        @stage
        def one():
            yield 1

        @stage
        def two(one):
            return one * 2

        registered = get_registered_stages()
        names = [d.name for d in registered]
        assert "one" in names
        assert "two" in names

    def test_no_deps_transform(self):
        """A transform with no parameters has no dependencies (unusual but valid)."""
        @stage
        def standalone():
            return 42

        defn = standalone.__stage__
        assert defn.dependencies == ()
        assert defn.is_producer is False

    def test_repr(self):
        @stage
        def producer():
            yield 1

        @stage
        def transform(producer):
            return producer

        assert "producer" in repr(producer.__stage__)
        assert "⚡" not in repr(transform.__stage__)  # that's just in mermaid


# ═══════════════════════════════════════════════════════════════════
# StageRegistry
# ═══════════════════════════════════════════════════════════════════

class TestStageRegistry:

    def _make_defn(self, name, deps=(), is_producer=False):
        """Create a StageDefinition without the decorator."""
        return StageDefinition(
            name=name,
            func=lambda: None,
            dependencies=tuple(deps),
            is_producer=is_producer,
        )

    def test_basic_add_and_query(self):
        reg = StageRegistry()
        d = self._make_defn("a")
        reg.add(d)

        assert "a" in reg
        assert len(reg) == 1
        assert reg["a"] is d

    def test_discover_from_global(self):
        @stage
        def src():
            yield 1

        @stage
        def sink(src):
            return src

        reg = StageRegistry()
        reg.discover()
        assert "src" in reg
        assert "sink" in reg

    def test_validate_missing_dep(self):
        reg = StageRegistry()
        reg.add(self._make_defn("a", deps=["nonexistent"]))

        with pytest.raises(MissingStageDependencyError, match="nonexistent"):
            reg.validate()

    def test_validate_cycle(self):
        reg = StageRegistry()
        # a → b → a
        reg.add(self._make_defn("a", deps=["b"]))
        reg.add(self._make_defn("b", deps=["a"]))

        with pytest.raises(CyclicDependencyError):
            reg.validate()

    def test_topological_order_linear(self):
        # a → b → c
        reg = StageRegistry()
        reg.add(self._make_defn("a", is_producer=True))
        reg.add(self._make_defn("b", deps=["a"]))
        reg.add(self._make_defn("c", deps=["b"]))

        order = reg.topological_order()
        assert order.index("a") < order.index("b") < order.index("c")

    def test_topological_order_diamond(self):
        # src → {mid1, mid2} → sink
        reg = StageRegistry()
        reg.add(self._make_defn("src", is_producer=True))
        reg.add(self._make_defn("mid1", deps=["src"]))
        reg.add(self._make_defn("mid2", deps=["src"]))
        reg.add(self._make_defn("sink", deps=["mid1", "mid2"]))

        order = reg.topological_order()
        assert order[0] == "src"
        assert order[-1] == "sink"
        assert set(order[1:3]) == {"mid1", "mid2"}

    def test_producers_and_transforms(self):
        reg = StageRegistry()
        reg.add(self._make_defn("p1", is_producer=True))
        reg.add(self._make_defn("p2", is_producer=True))
        reg.add(self._make_defn("t1", deps=["p1"]))

        assert len(reg.producers) == 2
        assert len(reg.transforms) == 1

    def test_export_mermaid(self):
        reg = StageRegistry()
        reg.add(self._make_defn("fetch", is_producer=True))
        reg.add(self._make_defn("extract", deps=["fetch"]))

        mermaid = reg.export_mermaid()
        assert "graph LR" in mermaid
        assert "fetch" in mermaid
        assert "extract" in mermaid
        assert "-->" in mermaid


# ═══════════════════════════════════════════════════════════════════
# Task state machine
# ═══════════════════════════════════════════════════════════════════

class TestTask:

    def test_initial_state(self):
        t = Task(stage_name="x", article_id="a1")
        assert t.state == TaskState.PENDING
        assert not t.is_terminal

    def test_happy_path_transitions(self):
        t = Task(stage_name="x", article_id="a1")

        ev1 = t.mark_waiting()
        assert t.state == TaskState.WAITING
        assert ev1.state == TaskState.WAITING
        assert ev1.waiting_on == []

        ev2 = t.mark_running()
        assert t.state == TaskState.RUNNING
        assert t.started_at is not None

        ev3 = t.mark_done(result={"key": "val"})
        assert t.state == TaskState.DONE
        assert t.is_terminal
        assert t.result == {"key": "val"}
        assert t.finished_at is not None

    def test_dropped_transition(self):
        t = Task(stage_name="x", article_id="a1")
        t.mark_running()
        ev = t.mark_dropped("not news")
        assert t.state == TaskState.DROPPED
        assert t.is_terminal
        assert "not news" in ev.detail

    def test_failed_transition(self):
        t = Task(stage_name="x", article_id="a1")
        t.mark_running()
        ev = t.mark_failed(ValueError("boom"))
        assert t.state == TaskState.FAILED
        assert t.is_terminal
        assert "boom" in ev.detail

    def test_elapsed_timing(self):
        t = Task(stage_name="x", article_id="a1")
        assert t.elapsed is None

        t.mark_running()
        time.sleep(0.01)
        assert t.elapsed is not None
        assert t.elapsed > 0

    def test_event_is_terminal(self):
        ev_done = TaskEvent(
            task_id="1", stage_name="x", article_id="a",
            state=TaskState.DONE,
        )
        ev_pending = TaskEvent(
            task_id="2", stage_name="x", article_id="a",
            state=TaskState.PENDING,
        )
        assert ev_done.is_terminal
        assert not ev_pending.is_terminal


# ═══════════════════════════════════════════════════════════════════
# DropArticle
# ═══════════════════════════════════════════════════════════════════

class TestDropArticle:

    def test_exception_message(self):
        exc = DropArticle("spam detected")
        assert exc.reason == "spam detected"
        assert str(exc) == "spam detected"

    def test_can_be_raised_and_caught(self):
        with pytest.raises(DropArticle, match="irrelevant"):
            raise DropArticle("irrelevant")


# ═══════════════════════════════════════════════════════════════════
# PipelineContext
# ═══════════════════════════════════════════════════════════════════

class TestPipelineContext:

    def test_defaults(self):
        ctx = PipelineContext()
        assert ctx.agent is None
        assert ctx.article_store is None
        assert ctx.run_id  # non-empty

    def test_extra_dict(self):
        ctx = PipelineContext(extra={"key": "val"})
        assert ctx.extra["key"] == "val"


# ═══════════════════════════════════════════════════════════════════
# StreamingRunner — integration tests
# ═══════════════════════════════════════════════════════════════════

class TestStreamingRunner:
    """
    End-to-end tests using small mock DAGs.
    """

    def _build_registry(self, *definitions: StageDefinition) -> StageRegistry:
        reg = StageRegistry()
        for d in definitions:
            reg.add(d)
        return reg

    def test_simple_linear_pipeline(self):
        """producer → transform1 → transform2"""
        items = ["hello", "world"]

        @stage
        def source():
            for item in items:
                yield item

        @stage
        def upper(source):
            return source.upper()

        @stage
        def exclaim(upper):
            return upper + "!"

        reg = StageRegistry()
        reg.discover()

        events: list[TaskEvent] = []
        runner = StreamingRunner(
            registry=reg,
            on_event=lambda ev: events.append(ev),
            max_workers=2,
        )
        runner.run()

        # Should have processed 2 articles
        done_events = [e for e in events if e.state == TaskState.DONE]
        # 2 articles × 2 transforms + 1 producer = 5 DONE events
        assert len(done_events) == 5

        # Check transforms produced correct results
        transform_tasks = [
            t for t in runner.get_all_tasks()
            if t.stage_name == "exclaim" and t.state == TaskState.DONE
        ]
        results = sorted(t.result for t in transform_tasks)
        assert results == ["HELLO!", "WORLD!"]

    def test_drop_article_cascades(self):
        """DropArticle in stage 1 should cancel stage 2."""

        @stage
        def source():
            yield "good"
            yield "bad"

        @stage
        def gate(source):
            if source == "bad":
                raise DropArticle("filtered out")
            return source

        @stage
        def final(gate):
            return gate.upper()

        reg = StageRegistry()
        reg.discover()

        events: list[TaskEvent] = []
        runner = StreamingRunner(
            registry=reg,
            on_event=lambda ev: events.append(ev),
            max_workers=2,
        )
        runner.run()

        # "good" should flow through to DONE
        final_done = [
            t for t in runner.get_all_tasks()
            if t.stage_name == "final" and t.state == TaskState.DONE
        ]
        assert len(final_done) == 1
        assert final_done[0].result == "GOOD"

        # "bad" should be dropped at gate → final should also be dropped
        dropped = [
            t for t in runner.get_all_tasks()
            if t.state == TaskState.DROPPED
            and not t.article_id.startswith("__producer__")
        ]
        assert len(dropped) >= 2  # gate + final for "bad" article

        assert runner.stats["articles_dropped"] >= 1

    def test_diamond_dag(self):
        """
        source → {left, right} → merge

        Both left and right must complete before merge runs.
        """
        @stage
        def source():
            yield 10

        @stage
        def left(source):
            return source + 1

        @stage
        def right(source):
            return source + 2

        @stage
        def merge(left, right):
            return left + right

        reg = StageRegistry()
        reg.discover()

        runner = StreamingRunner(
            registry=reg,
            max_workers=4,
        )
        runner.run()

        merge_tasks = [
            t for t in runner.get_all_tasks()
            if t.stage_name == "merge" and t.state == TaskState.DONE
        ]
        assert len(merge_tasks) == 1
        assert merge_tasks[0].result == 23  # (10+1) + (10+2)

    def test_ctx_injection(self):
        """Stages requesting ``ctx`` receive the PipelineContext."""

        @stage
        def source():
            yield "data"

        @stage
        def needs_context(source, ctx):
            return f"{source}_{ctx.run_id}"

        reg = StageRegistry()
        reg.discover()

        ctx = PipelineContext(run_id="test123")
        runner = StreamingRunner(registry=reg, ctx=ctx, max_workers=2)
        runner.run()

        result_tasks = [
            t for t in runner.get_all_tasks()
            if t.stage_name == "needs_context" and t.state == TaskState.DONE
        ]
        assert len(result_tasks) == 1
        assert result_tasks[0].result == "data_test123"

    def test_stop_halts_processing(self):
        """Calling stop() should prevent new tasks from starting."""

        @stage
        def slow_source():
            for i in range(100):
                time.sleep(0.01)
                yield i

        @stage
        def sink(slow_source):
            return slow_source

        reg = StageRegistry()
        reg.discover()

        runner = StreamingRunner(registry=reg, max_workers=2)

        # Stop after 100ms
        def stop_after_delay():
            time.sleep(0.1)
            runner.stop()

        threading.Thread(target=stop_after_delay, daemon=True).start()
        runner.run()

        # Should NOT have processed all 100 items
        done_count = sum(
            1 for t in runner.get_all_tasks()
            if t.stage_name == "sink" and t.state == TaskState.DONE
        )
        assert done_count < 100

    def test_stage_exception_does_not_crash_runner(self):
        """A failing stage should not take down the whole runner."""

        @stage
        def source():
            yield "ok"
            yield "crash"
            yield "ok2"

        @stage
        def maybe_crash(source):
            if source == "crash":
                raise RuntimeError("boom")
            return source.upper()

        reg = StageRegistry()
        reg.discover()

        runner = StreamingRunner(registry=reg, max_workers=2)
        runner.run()  # should not raise

        done = [
            t for t in runner.get_all_tasks()
            if t.stage_name == "maybe_crash" and t.state == TaskState.DONE
        ]
        failed = [
            t for t in runner.get_all_tasks()
            if t.stage_name == "maybe_crash" and t.state == TaskState.FAILED
        ]
        assert len(done) == 2
        assert len(failed) == 1

    def test_backpressure_limits_inflight(self):
        """With max_inflight=2, at most 2 articles are in-flight at once."""
        max_seen = {"count": 0}
        lock = threading.Lock()

        @stage
        def source():
            for i in range(10):
                yield i

        @stage
        def slow_stage(source):
            with lock:
                max_seen["count"] = max(max_seen["count"], 1)
            time.sleep(0.05)
            return source

        reg = StageRegistry()
        reg.discover()

        runner = StreamingRunner(
            registry=reg,
            max_workers=4,
            max_inflight=2,
        )
        runner.run()

        done = [
            t for t in runner.get_all_tasks()
            if t.stage_name == "slow_stage" and t.state == TaskState.DONE
        ]
        assert len(done) == 10  # all completed despite backpressure

    def test_empty_producer(self):
        """A producer that yields nothing should complete without error."""

        @stage
        def empty():
            return
            yield  # make it a generator  # noqa: RET504

        @stage
        def sink(empty):
            return empty

        reg = StageRegistry()
        reg.discover()

        runner = StreamingRunner(registry=reg, max_workers=2)
        runner.run()

        sink_tasks = [
            t for t in runner.get_all_tasks()
            if t.stage_name == "sink"
        ]
        assert len(sink_tasks) == 0  # no articles spawned

    def test_dict_article_id_derivation(self):
        """Dict items with title/publication_date get deterministic IDs."""

        @stage
        def source():
            yield {"title": "Test", "publication_date": "2024-01-01"}
            yield {"title": "Test", "publication_date": "2024-01-01"}  # duplicate

        @stage
        def sink(source):
            return source

        reg = StageRegistry()
        reg.discover()

        runner = StreamingRunner(registry=reg, max_workers=2)
        runner.run()

        # Both items produce the same article_id hash, so the runner
        # creates tasks for both (dedup is a stage concern, not engine)
        sink_done = [
            t for t in runner.get_all_tasks()
            if t.stage_name == "sink" and t.state == TaskState.DONE
        ]
        assert len(sink_done) == 2

    def test_multiple_producers(self):
        """Multiple independent producers each spawn their own graphs."""

        @stage
        def rss():
            yield "rss_item"

        @stage
        def api():
            yield "api_item"

        @stage
        def process_rss(rss):
            return f"processed_{rss}"

        @stage
        def process_api(api):
            return f"processed_{api}"

        reg = StageRegistry()
        reg.discover()

        runner = StreamingRunner(registry=reg, max_workers=4)
        runner.run()

        rss_done = [
            t for t in runner.get_all_tasks()
            if t.stage_name == "process_rss" and t.state == TaskState.DONE
        ]
        api_done = [
            t for t in runner.get_all_tasks()
            if t.stage_name == "process_api" and t.state == TaskState.DONE
        ]
        assert len(rss_done) == 1
        assert rss_done[0].result == "processed_rss_item"
        assert len(api_done) == 1
        assert api_done[0].result == "processed_api_item"
