import os
import re
import time
import threading
from textual.app import App, ComposeResult
from textual.widget import Widget
from textual.widgets import Header, Footer, Static, RichLog, ProgressBar, Button
from textual.containers import Horizontal, Vertical, ScrollableContainer, Grid
from textual.binding import Binding
from textual.worker import get_current_worker
from textual import work
from rich.markup import escape

try:
    import pipeline.stages  # noqa: F401
except ImportError:
    pass

from pipeline.runner import (
    PipelineRunner,
    PipelineEvent,
    StageStarted,
    StageProgress,
    StageCompleted,
    LogEvent,
    SOURCE_REGISTRY,
)
from pipeline.engine.task import TaskEvent, TaskState
from service.logger import Logger
from service.db import FileStore
from config import config
from pipeline.tui.screens.articles import ArticlesScreen


STAGE_DEFS = [
    # (stage_id, display_name, upstream_dependency)
    # Producers
    ("fetch_reddit", "fetch_reddit", None),
    ("fetch_gnews", "fetch_gnews", None),
    ("scrape_targets", "scrape_targets", None),
    ("fetch_rapid_news", "fetch_rapid_news", None),
    ("fetch_media_stack", "fetch_media_stack", None),
    ("fetch_news_org", "fetch_news_org", None),
    ("fetch_core", "fetch_core", None),
    # Transforms
    ("parse", "parse", "sources"),
    ("dedup", "dedup", "parse"),
    ("classify", "classify", "dedup"),
    ("extract", "extract", "classify"),
    ("format_markdown", "format", "extract"),
    ("embed", "embed", "format"),
    ("persist", "persist", "embed"),
]

STAGE_FALLBACK_DOCS = {
    "fetch_reddit": "Fetch top posts from configured subreddits.",
    "fetch_gnews": "Fetch articles from GNews API.",
    "scrape_targets": "Yield target URLs for web scraping.",
    "fetch_rapid_news": "Fetch news from RapidAPI Real-Time News.",
    "fetch_media_stack": "Fetch news from MediaStack API.",
    "fetch_news_org": "Fetch articles from NewsAPI.org.",
    "fetch_core": "Fetch papers from Core API.",
    "parse": "Parse a raw article item into a standardized dict.",
    "dedup": "Check if article already exists in the article store.",
    "classify": "Classify whether article is newsworthy.",
    "extract": "Extract structured article data using LLM.",
    "format_markdown": "Format article content as clean Markdown.",
    "embed": "Generate a vector embedding for the article.",
    "persist": "Save the processed article to the configured article store.",
}


def _get_stage_description(stage_id: str) -> str:
    """Retrieve the first line of the docstring for a stage."""
    from pipeline.engine.stage import get_registered_stages

    for s in get_registered_stages():
        if s.name == stage_id and s.doc:
            return s.doc.strip().splitlines()[0].strip()
    return STAGE_FALLBACK_DOCS.get(stage_id, "")


class TaskRow(Widget):
    """
    btop-style Task Manager Row without progress bars.
    Format:
    <display_name:20>  <items_text:20>  <elapsed_text:16>  <status:28>  <description>
    """

    def __init__(
        self,
        stage_id: str,
        display_name: str,
        upstream: str | None = None,
        description: str | None = None,
        **kwargs,
    ):
        super().__init__(id=f"row-{stage_id}", **kwargs)
        self.stage_id = stage_id
        self.display_name = display_name
        self.upstream = upstream
        self.description = (
            description if description is not None else _get_stage_description(stage_id)
        )
        self.done_count = 0
        self.start_time: float | None = None
        self.stage_disabled: bool = False

    def compose(self) -> ComposeResult:
        yield Static(self._format_line("[dim]Idle[/dim]"), id=f"lbl-{self.stage_id}", classes="task-line")

    def _format_line(self, status: str, elapsed: float | None = None) -> str:
        name_col = f"{self.display_name:<20}"
        desc = f"[dim]{escape(self.description)}[/dim]" if self.description else ""
        if getattr(self, "stage_disabled", False) or "Disabled" in status:
            plain_status = "Disabled"
            pad = " " * max(2, 28 - len(plain_status))
            status_col = f"[dim]Disabled[/dim]{pad}"
            return f"[bold #58a6ff]{name_col}[/bold #58a6ff]  {'-':<20}  {'-':<16}  {status_col}{desc}"
        items_col = f"{self.done_count} items parsed".ljust(20)
        if elapsed is not None:
            el = elapsed
        elif self.start_time is not None:
            el = time.monotonic() - self.start_time
        else:
            el = 0.0
        elapsed_col = f"{el:.1f}s elapsed".ljust(16)
        plain_status = re.sub(r"\[.*?\]", "", status)
        pad = " " * max(2, 28 - len(plain_status))
        status_col = f"{status}{pad}"
        return f"[bold #58a6ff]{name_col}[/bold #58a6ff]  {items_col}  {elapsed_col}  {status_col}{desc}"

    def set_waiting(self, upstream: str | None = None) -> None:
        if getattr(self, "stage_disabled", False):
            return
        self.remove_class("running")
        target = upstream or self.upstream or "sources"
        parts = [p.strip() for p in target.split(",")]
        clean = [p for p in parts if not (len(p) in (8, 12, 16, 32, 36) and all(c in "0123456789abcdefABCDEF-" for c in p))]
        final_target = ", ".join(clean) if clean else (self.upstream or "sources")
        self.query_one(f"#lbl-{self.stage_id}", Static).update(
            self._format_line(f"[yellow]WAITING FOR {final_target}[/yellow]")
        )

    def set_stopped(self) -> None:
        if getattr(self, "stage_disabled", False):
            return
        self.remove_class("running")
        self.query_one(f"#lbl-{self.stage_id}", Static).update(
            self._format_line("[dim]Stopped[/dim]")
        )

    def set_running(self, current: int = 0, total: int | None = None, elapsed: float | None = None) -> None:
        if getattr(self, "stage_disabled", False):
            return
        self.add_class("running")
        if self.start_time is None:
            self.start_time = time.monotonic()
        if current > self.done_count:
            self.done_count = current
        self.query_one(f"#lbl-{self.stage_id}", Static).update(
            self._format_line("[cyan]● RUNNING[/cyan]", elapsed=elapsed)
        )

    def record_progress(self, current: int, total: int | None = None) -> None:
        if getattr(self, "stage_disabled", False):
            return
        self.done_count = current
        self.add_class("running")
        if self.start_time is None:
            self.start_time = time.monotonic()
        self.query_one(f"#lbl-{self.stage_id}", Static).update(
            self._format_line("[cyan]● RUNNING[/cyan]")
        )

    def set_done(self, count: int | None = None, elapsed: float | None = None) -> None:
        if getattr(self, "stage_disabled", False):
            return
        self.remove_class("running")
        if count is not None:
            self.done_count = count
        el = elapsed if elapsed is not None else (time.monotonic() - (self.start_time or time.monotonic()))
        self.query_one(f"#lbl-{self.stage_id}", Static).update(
            self._format_line(f"[green]✓ Done ({self.done_count})[/green]", elapsed=el)
        )

    def set_disabled(self) -> None:
        self.stage_disabled = True
        self.remove_class("running")
        self.query_one(f"#lbl-{self.stage_id}", Static).update(
            self._format_line("[dim]Disabled[/dim]")
        )

    def set_failed(self, error: str | None = None) -> None:
        if getattr(self, "stage_disabled", False):
            return
        self.remove_class("running")
        err_msg = f": {error}" if error else ""
        self.query_one(f"#lbl-{self.stage_id}", Static).update(
            self._format_line(f"[red]✗ Failed{err_msg}[/red]")
        )

    def reset(self) -> None:
        self.stage_disabled = False
        self.done_count = 0
        self.start_time = None
        self.remove_class("running")
        self.query_one(f"#lbl-{self.stage_id}", Static).update(
            self._format_line("[dim]Idle[/dim]")
        )


class DistillNewsApp(App):
    TITLE = "DistillNews"
    CSS_PATH = "styles/app.tcss"

    BINDINGS = [
        Binding("b", "toggle_logs", "View Logs", priority=True),
        Binding("p", "toggle_run", "Run/Stop", priority=True),
        Binding("x", "stop", "Stop Tasks", priority=True),
        Binding("a", "articles", "Articles", priority=True),
        Binding("q", "quit", "Quit", priority=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        backend = config.ARTICLE_STORE_BACKEND
        backend_label = "Azure Blob" if backend == "azure" else "Local Disk"

        with Grid(id="app-grid"):
            # ── Left Sidebar (Pure Configuration) ───────────────────────────
            with ScrollableContainer(id="sidebar"):
                yield Static("Pipeline Control", id="lbl-pipeline-control", classes="stage-label panel-title-red")
                # Single interchangeable RUN / STOP button
                yield Button("▶ RUN PIPELINE", id="btn-run-stop", variant="primary")

                yield Static("\nStorage Backend", classes="stage-label")
                yield Button(
                    f"Store: {backend_label}",
                    id="btn-toggle-store",
                    variant="warning" if backend == "azure" else "default",
                )

                yield Static("\nStages (Click to Toggle)", classes="stage-label")
                with Vertical(id="stages-container"):
                    fetch_enabled = config.is_stage_enabled("fetch")
                    yield Button(
                        "Fetch",
                        id="btn-stage-fetch",
                        variant="success" if fetch_enabled else "default",
                    )
                    scrape_enabled = config.is_stage_enabled("scrape")
                    yield Button(
                        "Scrape",
                        id="btn-stage-scrape",
                        variant="success" if scrape_enabled else "default",
                    )

                yield Static("\nSources (Click to Toggle)", classes="stage-label")
                with Vertical(id="sources-container"):
                    for name in sorted(SOURCE_REGISTRY.keys()):
                        enabled = config.is_source_enabled(name)
                        variant = "success" if enabled else "default"
                        yield Button(name, id=f"btn-src-{name}", variant=variant)

                yield Static("\nData", classes="stage-label")
                yield Static("0 articles processed", id="article-count")
                yield Button("Browse Articles", id="btn-articles", variant="success")

            # ── Right Top Panel (btop-style Task Manager) ───────────────────
            with ScrollableContainer(id="main-panel", can_focus=True):
                yield Static("Pipeline Task Manager", id="lbl-task-manager", classes="stage-label panel-title-red")

                # Task Rows for each stage in the pipeline DAG
                with Vertical(id="task-manager-container"):
                    for stage_id, display_name, upstream in STAGE_DEFS:
                        yield TaskRow(stage_id=stage_id, display_name=display_name, upstream=upstream)

            # ── Right Bottom Panel (Live Event Logs) ────────────────────────
            with Vertical(id="log-panel"):
                yield RichLog(id="main-log", highlight=True, markup=True)

        yield Footer()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._is_quitting = False
        self._is_running = False
        self._current_runner = None
        self._stage_done_counts: dict[str, int] = {}

    def on_mount(self) -> None:
        Logger.add_listener(self._handle_log)
        self._update_article_count()
        try:
            self.query_one("#main-panel").focus()
        except Exception:
            pass

    def on_unmount(self) -> None:
        self._is_quitting = True
        Logger.remove_listener(self._handle_log)
        self.workers.cancel_all()

    def action_quit(self) -> None:
        self._is_quitting = True
        try:
            self.workers.cancel_all()
        except Exception:
            pass
        self.exit()

    def action_toggle_logs(self) -> None:
        """Toggle focus between Task Manager panel and Logs panel."""
        try:
            log = self.query_one("#main-log", RichLog)
            panel = self.query_one("#main-panel", ScrollableContainer)
            if log.has_focus:
                panel.focus()
            else:
                log.focus()
        except Exception:
            pass

    def action_toggle_sidebar(self) -> None:
        try:
            sidebar = self.query_one("#sidebar")
            grid = self.query_one("#app-grid")
            sidebar.display = not sidebar.display
            if not sidebar.display:
                grid.add_class("sidebar-hidden")
                self._handle_log("INFO", "Sidebar collapsed.", None)
            else:
                grid.remove_class("sidebar-hidden")
                self._handle_log("INFO", "Sidebar expanded.", None)
        except Exception:
            pass

    def _handle_log(self, badge: str, message: str, detail: str | None = None) -> None:
        if self._is_quitting or getattr(self, "_unmounted", False):
            return
        try:
            log_widget = self.query_one("#main-log", RichLog)
        except Exception:
            return

        colors = {
            "INFO": "#58a6ff",
            "SUCCESS": "#3fb950",
            "WARN": "#d29922",
            "ERROR": "#f85149",
            "FAIL": "#f85149",
            "STAGE": "#a371f7",
            "SKIP": "#8b949e",
            "DONE": "#3fb950",
        }
        color = colors.get(badge.upper(), "#c9d1d9")
        timestamp = time.strftime("%H:%M:%S")

        prefix = f"[dim]{timestamp}[/dim] [{color}][bold][{badge.upper()}][/{color}][/bold] "
        try:
            from rich.text import Text
            test_markup = f"{prefix}{message}"
            Text.from_markup(test_markup)
            formatted_message = test_markup
        except Exception:
            formatted_message = f"{prefix}{escape(message)}"

        if detail:
            try:
                from rich.text import Text
                detail_markup = f"\n   [dim]{detail}[/dim]"
                Text.from_markup(detail_markup)
                formatted_message += detail_markup
            except Exception:
                formatted_message += f"\n   [dim]{escape(detail)}[/dim]"

        if threading.get_ident() == self._thread_id:
            log_widget.write(formatted_message)
        else:
            try:
                self.call_from_thread(log_widget.write, formatted_message)
            except Exception:
                pass

    def _update_article_count(self) -> None:
        self._update_article_count_worker()

    @work(thread=True)
    def _update_article_count_worker(self) -> None:
        if self._is_quitting:
            return
        try:
            from service.db import create_article_store
            article_store = create_article_store()
            articles = article_store.list_articles()
            count = len(articles)
            lbl = self.query_one("#article-count", Static)
            text = f"{count} articles processed"
            self.call_from_thread(lbl.update, text)
        except Exception:
            pass

    def _handle_event(self, event: PipelineEvent | TaskEvent) -> None:
        if self._is_quitting:
            return

        # 1. Granular TaskEvent from streaming engine
        if isinstance(event, TaskEvent):
            stage_name = event.stage_name
            try:
                row = self.query_one(f"#row-{stage_name}", TaskRow)
            except Exception:
                return

            if event.state == TaskState.WAITING:
                clean_waiting = []
                for w in (event.waiting_on or []):
                    # Discard any raw task ID hex hashes (e.g. 8, 12, 16, 32, 36 hex chars)
                    if len(w) in (8, 12, 16, 32, 36) and all(c in "0123456789abcdefABCDEF-" for c in w):
                        continue
                    clean_waiting.append(w)
                upstream_info = ", ".join(clean_waiting) if clean_waiting else None
                row.set_waiting(upstream_info)
            elif event.state == TaskState.RUNNING:
                res = getattr(event, "result", None)
                if res and isinstance(res, dict) and "count" in res:
                    cnt = res["count"]
                    self._stage_done_counts[stage_name] = cnt
                else:
                    cnt = self._stage_done_counts.get(stage_name, 0)
                row.set_running(current=cnt)
            elif event.state == TaskState.DONE:
                res = getattr(event, "result", None)
                if res and isinstance(res, dict) and "count" in res:
                    cnt = res["count"]
                else:
                    cnt = self._stage_done_counts.get(stage_name, 0) + 1
                self._stage_done_counts[stage_name] = cnt
                row.set_done(count=cnt)
                if stage_name == "persist":
                    self._update_article_count()
            elif event.state == TaskState.DROPPED:
                pass
            elif event.state == TaskState.FAILED:
                row.set_failed(event.detail)

        # 2. Traditional Pipeline Events
        elif isinstance(event, StageStarted):
            pass

        elif isinstance(event, StageProgress):
            pass

        elif isinstance(event, StageCompleted):
            if event.stage == "embed" or event.stage == "pipeline":
                self._update_article_count()
                self._set_idle_state()

        elif isinstance(event, LogEvent):
            self._handle_log(event.badge, event.message, event.detail)

    def _set_running_state(self) -> None:
        """Update button and state to Running."""
        self._is_running = True
        try:
            btn = self.query_one("#btn-run-stop", Button)
            btn.label = "■ STOP"
            btn.variant = "error"
        except Exception:
            pass

    def _set_idle_state(self) -> None:
        """Update button and state to Idle."""
        self._is_running = False
        try:
            btn = self.query_one("#btn-run-stop", Button)
            btn.label = "▶ RUN PIPELINE"
            btn.variant = "primary"
        except Exception:
            pass

    def action_toggle_run(self) -> None:
        """Toggle between Run and Stop."""
        if self._is_running:
            self.action_stop()
        else:
            self.action_run()

    def action_run(self) -> None:
        """Initialize task rows and run the streaming pipeline."""
        self._set_running_state()
        self._stage_done_counts.clear()

        # Initialize all task rows: transforms to WAITING, producers to RUNNING or DISABLED
        for stage_id, _, upstream in STAGE_DEFS:
            try:
                row = self.query_one(f"#row-{stage_id}", TaskRow)
                # Check if producer is disabled in config
                if upstream is None:
                    # Producer stage
                    if stage_id.startswith("fetch_") and not config.is_stage_enabled("fetch"):
                        row.set_disabled()
                    elif stage_id == "scrape_targets" and not config.is_stage_enabled("scrape"):
                        row.set_disabled()
                    else:
                        source_key = stage_id.removeprefix("fetch_").replace("scrape_targets", "scrape")
                        if not config.is_source_enabled(source_key):
                            row.set_disabled()
                        else:
                            row.set_running(current=0)
                else:
                    # Transform stage waiting for upstream
                    row.set_waiting(upstream)
            except Exception:
                pass

        self._handle_log("INFO", "Starting streaming pipeline...", None)
        self._run_pipeline("run_all")

    def action_stop(self) -> None:
        """Stop active workers and mark tasks stopped."""
        self._is_running = False
        if getattr(self, "_current_runner", None):
            try:
                self._current_runner.stop()
            except Exception:
                pass
        self.workers.cancel_group(self, "pipeline")
        self.workers.cancel_all()
        self._set_idle_state()

        # Immediately update all running / waiting task rows to Stopped in the UI
        for stage_id, _, _ in STAGE_DEFS:
            try:
                row = self.query_one(f"#row-{stage_id}", TaskRow)
                lbl = row.query_one(f"#lbl-{stage_id}", Static)
                lbl_text = str(lbl._render())
                if row.has_class("running") or "WAITING" in lbl_text:
                    row.set_stopped()
            except Exception:
                pass

        self._handle_log("WARN", "Pipeline cancelled by user.", None)

    def action_articles(self) -> None:
        self.push_screen(ArticlesScreen())

    def _run_pipeline(self, method_name: str) -> None:
        self.workers.cancel_group(self, "pipeline")

        def _emit_event(e: PipelineEvent | TaskEvent) -> None:
            if self._is_quitting or getattr(self, "_unmounted", False):
                return
            if threading.get_ident() == self._thread_id:
                self._handle_event(e)
            else:
                try:
                    self.call_from_thread(self._handle_event, e)
                except Exception:
                    pass

        def _run():
            worker = get_current_worker()

            def _should_stop() -> bool:
                return (
                    not self._is_running
                    or self._is_quitting
                    or getattr(self, "_unmounted", False)
                    or (worker is not None and worker.is_cancelled)
                )

            runner = PipelineRunner(callback=_emit_event, stop_checker=_should_stop)
            self._current_runner = runner
            try:
                runner.run_streaming()
            finally:
                self._current_runner = None
                if not _should_stop():
                    self.call_from_thread(self._set_idle_state)

        self.run_worker(_run, thread=True, group="pipeline", name=method_name, exclusive=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id == "btn-run-stop":
            self.action_toggle_run()
        elif button_id == "btn-articles":
            self.action_articles()
        elif button_id == "btn-toggle-store":
            current_backend = config.ARTICLE_STORE_BACKEND
            new_backend = "azure" if current_backend == "file" else "file"
            os.environ["ARTICLE_STORE_BACKEND"] = new_backend
            label = "Azure Blob" if new_backend == "azure" else "Local Disk"
            event.button.label = f"Store: {label}"
            event.button.variant = "warning" if new_backend == "azure" else "default"
            self._handle_log("INFO", f"Article store switched to [bold]{new_backend}[/bold]", None)
            self._update_article_count()
        elif button_id in ("btn-stage-fetch", "btn-stage-scrape"):
            stage_name = "fetch" if button_id == "btn-stage-fetch" else "scrape"
            new_status = config.toggle_stage(stage_name)
            event.button.variant = "success" if new_status else "default"
            status_str = "[green]ENABLED[/green]" if new_status else "[dim]DISABLED[/dim]"
            display_name = "Fetch" if stage_name == "fetch" else "Scrape"
            self._handle_log("INFO", f"Stage '{display_name}' is now {status_str}", None)
        elif button_id.startswith("btn-src-"):
            source_name = button_id.removeprefix("btn-src-")
            new_status = config.toggle_source(source_name)
            event.button.label = source_name
            event.button.variant = "success" if new_status else "default"
            status_str = "[green]ENABLED[/green]" if new_status else "[dim]DISABLED[/dim]"
            self._handle_log("INFO", f"Source '{source_name}' is now {status_str}", None)
