"""
Streaming pipeline runner — executes the stage DAG with per-article
parallelism and backpressure.

Design:
  - Each item yielded by a producer stage spawns an independent
    "article graph" — a copy of the transform DAG wired to that item.
  - Tasks are dispatched to a ``ThreadPoolExecutor`` as soon as all
    their upstream tasks complete.
  - A bounded queue provides backpressure so fast producers don't
    overwhelm slow downstream stages.
  - Every state transition emits a ``TaskEvent`` to a callback,
    enabling the TUI task-manager view.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable

from pipeline.engine.stage import StageDefinition, INJECTED_PARAMS
from pipeline.engine.registry import StageRegistry
from pipeline.engine.task import (
    DropArticle,
    PipelineContext,
    Task,
    TaskEvent,
    TaskState,
)


class StreamingRunner:
    """
    Execute a validated ``StageRegistry`` as a streaming pipeline.

    Args:
        registry:      A populated and validated ``StageRegistry``.
        ctx:           ``PipelineContext`` injected into stages that
                       request a ``ctx`` parameter.
        max_workers:   Thread pool size.
        on_event:      Optional callback invoked for every ``TaskEvent``.
        max_inflight:  Backpressure cap — max article graphs in flight.
    """

    def __init__(
        self,
        registry: StageRegistry,
        ctx: PipelineContext | None = None,
        max_workers: int = 8,
        on_event: Callable[[TaskEvent], None] | None = None,
        max_inflight: int = 64,
        stop_checker: Callable[[], bool] | None = None,
    ) -> None:
        self.registry = registry
        self.ctx = ctx or PipelineContext()
        self.max_workers = max_workers
        self.on_event = on_event
        self.max_inflight = max_inflight
        self.stop_checker = stop_checker

        # Execution order (pre-computed once)
        self._order = registry.topological_order()

        # Pre-compute reachable stages from each producer (for multi-producer DAGs)
        self._reachable_from: dict[str, set[str]] = {}
        for producer in registry.producers:
            reachable: set[str] = set()
            frontier = [producer.name]

            # Transform stages with stream dependencies are reachable from any producer
            for defn in registry.transforms:
                if getattr(defn, "stream_dependencies", ()):
                    reachable.add(defn.name)
                    frontier.append(defn.name)

            while frontier:
                current = frontier.pop()
                for defn in registry:
                    if defn.name in reachable:
                        continue
                    if current in defn.dependencies:
                        reachable.add(defn.name)
                        frontier.append(defn.name)
            self._reachable_from[producer.name] = reachable

        # ── shared mutable state (protected by _lock) ──────────────
        self._lock = threading.Lock()
        self._tasks: dict[str, Task] = {}                 # task_id → Task
        self._article_tasks: dict[str, list[str]] = defaultdict(list)  # article_id → [task_ids]
        self._article_titles: dict[str, str] = {}         # article_id → title
        self._pending_futures: dict[str, Future[Any]] = {}
        self._inflight_count = 0
        self._inflight_sem = threading.Semaphore(max_inflight)

        # Cancellation
        self._stop_event = threading.Event()

        # Statistics
        self.stats: dict[str, int] = defaultdict(int)

    # ── public API ──────────────────────────────────────────────────

    def run(self) -> None:
        """
        Start the pipeline.

        Launches all producer stages, then blocks until every spawned
        task has reached a terminal state or ``stop()`` is called.
        """
        self.registry.validate()

        producers = self.registry.producers
        if not producers:
            return

        pool = ThreadPoolExecutor(max_workers=self.max_workers)
        self._pool = pool
        producer_pool = ThreadPoolExecutor(max_workers=max(len(producers), 1))
        self._producer_pool = producer_pool

        try:
            # Launch each producer in its own thread in producer_pool
            producer_futures: list[Future[None]] = []
            for defn in producers:
                if self.is_stopped:
                    break
                f = producer_pool.submit(self._run_producer, defn)
                producer_futures.append(f)

            # Wait for all producers to finish yielding with responsive stop checking
            while not self.is_stopped:
                if all(f.done() for f in producer_futures):
                    break
                time.sleep(0.05)

            # If stopped, cancel producer futures
            if self.is_stopped:
                for f in producer_futures:
                    f.cancel()
            else:
                # Now wait for all remaining in-flight tasks
                self._wait_for_completion()
        finally:
            producer_pool.shutdown(wait=False, cancel_futures=True)
            pool.shutdown(wait=False, cancel_futures=True)

    def stop(self) -> None:
        """Signal all threads to stop as soon as possible."""
        self._stop_event.set()
        with self._lock:
            for fut in list(self._pending_futures.values()):
                try:
                    fut.cancel()
                except Exception:
                    pass
        try:
            self._inflight_sem.release(self.max_inflight)
        except Exception:
            pass
        if hasattr(self, "_producer_pool") and self._producer_pool:
            try:
                self._producer_pool.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
        if hasattr(self, "_pool") and self._pool:
            try:
                self._pool.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass

    @property
    def is_stopped(self) -> bool:
        if self._stop_event.is_set():
            return True
        if self.stop_checker and self.stop_checker():
            self._stop_event.set()
            return True
        return False

    def get_all_tasks(self) -> list[Task]:
        """Snapshot of all tasks (for TUI rendering)."""
        with self._lock:
            return list(self._tasks.values())

    def get_article_tasks(self, article_id: str) -> list[Task]:
        """Get all tasks for a specific article."""
        with self._lock:
            return [self._tasks[tid] for tid in self._article_tasks.get(article_id, [])]

    # ── producer execution ──────────────────────────────────────────

    def _run_producer(self, defn: StageDefinition) -> None:
        """
        Execute a producer stage.  Each yielded item spawns a new
        article graph through the transform DAG.
        """
        producer_task = self._create_task(
            stage_name=defn.name,
            article_id=f"__producer__{defn.name}",
        )
        self._emit(producer_task.mark_running())

        count = 0
        try:
            gen = defn.func() if not _needs_ctx(defn) else defn.func(ctx=self.ctx)

            for item in gen:
                if self.is_stopped:
                    break

                count += 1
                # Backpressure: acquire with timeout so cancellation is responsive
                acquired = False
                while not self.is_stopped:
                    acquired = self._inflight_sem.acquire(timeout=0.1)
                    if acquired:
                        break
                if self.is_stopped:
                    if acquired:
                        self._inflight_sem.release()
                    break

                article_id = _derive_article_id(item)
                item_title = _extract_article_title(item)

                with self._lock:
                    self._inflight_count += 1
                    if item_title:
                        self._article_titles[article_id] = item_title

                self._spawn_article_graph(article_id, defn.name, item)
                self.stats["articles_spawned"] += 1
                self._emit(TaskEvent(
                    task_id=producer_task.id,
                    stage_name=defn.name,
                    article_id=f"__producer__{defn.name}",
                    state=TaskState.RUNNING,
                    result={"count": count},
                ))

            self._emit(producer_task.mark_done(result={"count": count}))

        except Exception as exc:
            self._emit(producer_task.mark_failed(exc))

    # ── article graph wiring ────────────────────────────────────────

    def _spawn_article_graph(
        self,
        article_id: str,
        producer_name: str,
        producer_output: Any,
    ) -> None:
        """
        Create one Task per transform stage for this article, wire up
        dependencies, and kick off any stages whose deps are already met.

        IMPORTANT: the entire graph is wired *before* any tasks are
        dispatched to the thread pool.  This prevents a race where a
        fast-completing task tries to unblock dependents that haven't
        been created yet.
        """
        # Map: stage_name → task for this article
        graph: dict[str, Task] = {}

        # Phase 1 — create all tasks and wire upstream dependencies
        reachable = self._reachable_from.get(producer_name, set())
        for stage_name in self._order:
            defn = self.registry[stage_name]
            if defn.is_producer:
                continue  # producers are already running
            if stage_name not in reachable:
                continue  # not reachable from this producer

            task = self._create_task(
                stage_name=stage_name,
                article_id=article_id,
            )
            graph[stage_name] = task

            # Wire upstream: find task IDs and names for each dependency
            for dep_name in defn.dependencies:
                if dep_name == producer_name:
                    # The producer output is already available — no
                    # upstream Task to wait for; we'll inject the value
                    # directly.
                    continue
                if dep_name in graph:
                    task.upstream_ids.append(graph[dep_name].id)
                    if dep_name not in task.upstream_names:
                        task.upstream_names.append(dep_name)

            for param_name, stream_type in getattr(defn, "stream_dependencies", ()):
                stream_name = getattr(stream_type, "__name__", str(stream_type))
                if stream_name not in task.upstream_names:
                    task.upstream_names.append(stream_name)

        # Store the producer output so dependents can grab it
        producer_result_key = f"_producer_{article_id}_{producer_name}"
        with self._lock:
            self._tasks[producer_result_key] = Task(
                id=producer_result_key,
                stage_name=producer_name,
                article_id=article_id,
                state=TaskState.DONE,
                result=producer_output,
            )

        # Phase 2 — mark non-ready tasks as WAITING, collect ready ones
        ready: list[Task] = []
        for stage_name, task in graph.items():
            if not task.upstream_ids:
                ready.append(task)
            else:
                self._emit(task.mark_waiting())

        # Phase 3 — dispatch ready tasks (graph is fully wired now)
        for task in ready:
            self._dispatch(task, graph, producer_name, producer_output)

    def _dispatch(
        self,
        task: Task,
        graph: dict[str, Task],
        producer_name: str,
        producer_output: Any,
    ) -> None:
        """Submit a task to the thread pool."""
        if self._stop_event.is_set():
            return

        defn = self.registry[task.stage_name]

        # Build kwargs by resolving each dependency
        kwargs = self._resolve_kwargs(defn, task, graph, producer_name, producer_output)

        def _execute(
            _task: Task = task,
            _defn: StageDefinition = defn,
            _kwargs: dict[str, Any] = kwargs,
            _graph: dict[str, Task] = graph,
            _producer_name: str = producer_name,
            _producer_output: Any = producer_output,
        ) -> None:
            self._execute_task(_task, _defn, _kwargs, _graph, _producer_name, _producer_output)

        future = self._pool.submit(_execute)
        with self._lock:
            self._pending_futures[task.id] = future

    def _resolve_kwargs(
        self,
        defn: StageDefinition,
        task: Task,
        graph: dict[str, Task],
        producer_name: str,
        producer_output: Any,
    ) -> dict[str, Any]:
        """
        Build the keyword arguments for a stage function by resolving
        each parameter name to the output of the corresponding upstream
        task (or to the producer output / ctx).
        """
        kwargs: dict[str, Any] = {}

        for param_name in defn.dependencies:
            if param_name == producer_name:
                kwargs[param_name] = producer_output
            elif param_name in graph:
                upstream_task = graph[param_name]
                kwargs[param_name] = upstream_task.result
            else:
                # Shouldn't happen after validation, but be safe
                kwargs[param_name] = None

        # Inject stream dependencies (e.g. article: RawArticle)
        for param_name, stream_type in getattr(defn, "stream_dependencies", ()):
            kwargs[param_name] = producer_output

        if _needs_ctx(defn):
            kwargs["ctx"] = self.ctx

        return kwargs

    # ── task execution ──────────────────────────────────────────────

    def _execute_task(
        self,
        task: Task,
        defn: StageDefinition,
        kwargs: dict[str, Any],
        graph: dict[str, Task],
        producer_name: str,
        producer_output: Any,
    ) -> None:
        """Run a single transform task and propagate results."""
        if self.is_stopped:
            task.state = TaskState.DROPPED
            task.drop_reason = "cancelled"
            self._emit(task.to_event("cancelled"))
            return

        self._emit(task.mark_running())

        try:
            result = defn.func(**kwargs)
            res_title = _extract_article_title(result)
            if res_title:
                with self._lock:
                    self._article_titles[task.article_id] = res_title
                task.article_title = res_title
                for t in graph.values():
                    if not t.article_title:
                        t.article_title = res_title

            self._emit(task.mark_done(result))
            self.stats["tasks_done"] += 1

        except DropArticle as drop:
            self._emit(task.mark_dropped(drop.reason))
            self.stats["articles_dropped"] += 1
            # Cancel all downstream tasks for this article
            self._cancel_downstream(task, graph)
            self._article_finished(task.article_id)
            return

        except Exception as exc:
            self._emit(task.mark_failed(exc))
            self.stats["tasks_failed"] += 1
            self._cancel_downstream(task, graph)
            self._article_finished(task.article_id)
            return

        # Check if any downstream tasks are now unblocked
        self._try_dispatch_dependents(task, graph, producer_name, producer_output)

        # Check if this article is fully done
        if self._is_article_done(task.article_id):
            self._article_finished(task.article_id)

    def _cancel_downstream(self, failed_task: Task, graph: dict[str, Task]) -> None:
        """
        Mark all tasks that transitively depend on ``failed_task`` as
        DROPPED (cascade).
        """
        cancelled_ids = {failed_task.id}
        changed = True
        while changed:
            changed = False
            for task in graph.values():
                if task.is_terminal:
                    continue
                if any(uid in cancelled_ids for uid in task.upstream_ids):
                    reason = f"upstream {failed_task.stage_name} {failed_task.state.name.lower()}"
                    self._emit(task.mark_dropped(reason))
                    cancelled_ids.add(task.id)
                    changed = True

    def _try_dispatch_dependents(
        self,
        completed_task: Task,
        graph: dict[str, Task],
        producer_name: str,
        producer_output: Any,
    ) -> None:
        """Dispatch any graph tasks whose upstream is now fully resolved."""
        for task in graph.values():
            if task.state != TaskState.WAITING:
                continue
            # Check if all upstream tasks are DONE
            all_done = all(
                self._tasks.get(uid, task).state == TaskState.DONE
                for uid in task.upstream_ids
            )
            if all_done:
                # Re-resolve kwargs now that upstreams have results
                defn = self.registry[task.stage_name]
                kwargs = self._resolve_kwargs(defn, task, graph, producer_name, producer_output)
                self._dispatch(task, graph, producer_name, producer_output)

    # ── lifecycle helpers ───────────────────────────────────────────

    def _create_task(self, stage_name: str, article_id: str) -> Task:
        with self._lock:
            title = self._article_titles.get(article_id, "")
            task = Task(stage_name=stage_name, article_id=article_id, article_title=title)
            self._tasks[task.id] = task
            self._article_tasks[article_id].append(task.id)
        return task

    def _emit(self, event: TaskEvent) -> None:
        if not getattr(event, "article_title", None):
            with self._lock:
                event.article_title = self._article_titles.get(event.article_id, "")
        if self.on_event:
            try:
                self.on_event(event)
            except Exception:
                pass  # never let a callback crash the runner

    def _is_article_done(self, article_id: str) -> bool:
        with self._lock:
            task_ids = self._article_tasks.get(article_id, [])
            return all(
                self._tasks[tid].is_terminal
                for tid in task_ids
                if not tid.startswith("_producer_")
            )

    def _article_finished(self, article_id: str) -> None:
        """Release the backpressure semaphore slot for this article."""
        with self._lock:
            self._inflight_count -= 1
        self._inflight_sem.release()
        self.stats["articles_completed"] += 1

    def _wait_for_completion(self) -> None:
        """Block until every non-producer task reaches a terminal state."""
        while True:
            if self._stop_event.is_set():
                break
            with self._lock:
                pending = [
                    t for t in self._tasks.values()
                    if not t.is_terminal
                    and not t.article_id.startswith("__producer__")
                    and not t.id.startswith("_producer_")
                ]
            if not pending:
                break
            time.sleep(0.05)


def _needs_ctx(defn: StageDefinition) -> bool:
    """Check whether the stage function wants a ``ctx`` parameter."""
    import inspect
    return "ctx" in inspect.signature(defn.func).parameters


def _derive_article_id(item: Any) -> str:
    """
    Best-effort article ID derivation from a producer's yielded item.

    Supports RawArticle instances, dicts with title/publication_date, or UUIDs.
    """
    from pipeline.engine.stream import RawArticle
    if isinstance(item, RawArticle):
        if item.article_id:
            return item.article_id
        title = item.get_title()
        pub_date = item.get_publication_date()
        if title:
            from hashlib import sha256
            key = f"{title}|{pub_date}"
            return sha256(key.encode()).hexdigest()[:16]
        if item.url:
            from hashlib import sha256
            return sha256(item.url.encode()).hexdigest()[:16]
    elif isinstance(item, dict):
        title = item.get("title", "")
        pub_date = item.get("publication_date", "")
        if title:
            from hashlib import sha256
            key = f"{title}|{pub_date}"
            return sha256(key.encode()).hexdigest()[:16]
    return uuid.uuid4().hex[:16]


def _extract_article_title(item: Any) -> str:
    """
    Best-effort extraction of article title from an item or task result.
    """
    from pipeline.engine.stream import RawArticle

    if isinstance(item, RawArticle):
        title = item.get_title()
        if title and str(title).strip().lower() != "unknown":
            return str(title).strip()
        if item.url:
            return str(item.url).strip()
    elif isinstance(item, dict):
        title = item.get("title")
        if title and str(title).strip().lower() != "unknown":
            return str(title).strip()
        payload = item.get("payload")
        if isinstance(payload, dict) and payload.get("title"):
            p_title = str(payload["title"]).strip()
            if p_title and p_title.lower() != "unknown":
                return p_title
        if item.get("url"):
            return str(item["url"]).strip()
    return ""

