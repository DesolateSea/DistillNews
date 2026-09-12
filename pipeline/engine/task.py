"""
Task primitives — state machine, events, and context for pipeline execution.

A Task represents a single stage executing on a single article.
Tasks transition through states: PENDING → WAITING → RUNNING → DONE/DROPPED/FAILED.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class TaskState(Enum):
    """Lifecycle states for a pipeline task."""

    PENDING = auto()     # registered but not yet eligible
    WAITING = auto()     # waiting for upstream dependencies
    RUNNING = auto()     # currently executing
    DONE = auto()        # completed successfully
    DROPPED = auto()     # article was dropped (DropArticle raised)
    FAILED = auto()      # stage raised an unexpected exception


class DropArticle(Exception):
    """
    Raise inside any stage to signal that this article should be
    removed from the pipeline.  All downstream tasks for the same
    article are cancelled.

    Usage::

        @stage
        def classify(raw_html: str) -> dict:
            if not is_newsworthy(raw_html):
                raise DropArticle("Not a news article")
            return parsed
    """

    def __init__(self, reason: str = ""):
        self.reason = reason
        super().__init__(reason)


@dataclass
class TaskEvent:
    """
    Immutable snapshot emitted whenever a task changes state.
    The TUI / CLI subscribe to a stream of these to render progress.
    """

    task_id: str
    stage_name: str
    article_id: str
    state: TaskState
    detail: str = ""
    timestamp: float = field(default_factory=time.time)
    waiting_on: list[str] = field(default_factory=list)
    result: Any = None
    article_title: str = ""

    @property
    def is_terminal(self) -> bool:
        return self.state in (TaskState.DONE, TaskState.DROPPED, TaskState.FAILED)


@dataclass
class Task:
    """
    A single unit of work: one stage applied to one article.

    The runner creates a Task for every (stage, article) combination.
    Tasks form a per-article DAG mirroring the stage DAG.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    stage_name: str = ""
    article_id: str = ""
    article_title: str = ""
    state: TaskState = TaskState.PENDING

    # Results and errors
    result: Any = None
    error: Exception | None = None
    drop_reason: str = ""

    # Timing
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None

    # DAG wiring (task IDs and names this task depends on)
    upstream_ids: list[str] = field(default_factory=list)
    upstream_names: list[str] = field(default_factory=list)

    def to_event(self, detail: str = "") -> TaskEvent:
        """Snapshot the current state as an immutable event."""
        waiting = []
        if self.state == TaskState.WAITING:
            waiting = list(self.upstream_names) if self.upstream_names else list(self.upstream_ids)
        return TaskEvent(
            task_id=self.id,
            stage_name=self.stage_name,
            article_id=self.article_id,
            state=self.state,
            detail=detail or self.drop_reason or (str(self.error) if self.error else ""),
            waiting_on=waiting,
            result=self.result,
            article_title=self.article_title,
        )

    # ── state transitions ──────────────────────────────────────────

    def mark_waiting(self) -> TaskEvent:
        self.state = TaskState.WAITING
        return self.to_event()

    def mark_running(self) -> TaskEvent:
        self.state = TaskState.RUNNING
        self.started_at = time.time()
        return self.to_event()

    def mark_done(self, result: Any) -> TaskEvent:
        self.state = TaskState.DONE
        self.result = result
        self.finished_at = time.time()
        if not self.article_title and isinstance(result, dict) and result.get("title"):
            t = str(result["title"]).strip()
            if t and t.lower() != "unknown":
                self.article_title = t
        return self.to_event()

    def mark_dropped(self, reason: str) -> TaskEvent:
        self.state = TaskState.DROPPED
        self.drop_reason = reason
        self.finished_at = time.time()
        return self.to_event(detail=reason)

    def mark_failed(self, error: Exception) -> TaskEvent:
        self.state = TaskState.FAILED
        self.error = error
        self.finished_at = time.time()
        return self.to_event(detail=str(error))

    @property
    def is_terminal(self) -> bool:
        return self.state in (TaskState.DONE, TaskState.DROPPED, TaskState.FAILED)

    @property
    def elapsed(self) -> float | None:
        if self.started_at is None:
            return None
        end = self.finished_at or time.time()
        return end - self.started_at


@dataclass
class PipelineContext:
    """
    Shared, read-only context available to every stage via dependency
    injection (request the parameter name ``ctx``).

    Stages that need configuration, the article store, or the agent
    receive them through this context rather than through global imports.
    """

    agent: Any = None
    article_store: Any = None
    config: Any = None
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    extra: dict[str, Any] = field(default_factory=dict)
    stop_checker: Any = None

    def is_stopped(self) -> bool:
        """Check if pipeline cancellation has been requested."""
        if self.stop_checker:
            try:
                return bool(self.stop_checker())
            except Exception:
                return False
        return False
