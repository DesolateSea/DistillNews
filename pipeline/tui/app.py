import os
import time
import threading
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, RichLog, ProgressBar, Button
from textual.containers import Horizontal, Vertical, ScrollableContainer, Grid
from textual.binding import Binding
from textual.worker import get_current_worker
from textual import work
from rich.markup import escape

from pipeline.runner import (
    PipelineRunner,
    PipelineEvent,
    StageStarted,
    StageProgress,
    StageCompleted,
    LogEvent,
    SOURCE_REGISTRY
)
from service.logger import Logger
from service.db import FileStore
from config import config
from pipeline.tui.screens.articles import ArticlesScreen


class Dashboard(Static):
    pass


class DistillNewsApp(App):
    TITLE = "DistillNews"
    CSS_PATH = "styles/app.tcss"

    BINDINGS = [
        Binding("b", "toggle_sidebar", "Sidebar (b)", priority=True),
        Binding("f", "fetch", "Fetch", priority=True),
        Binding("s", "scrape", "Scrape", priority=True),
        Binding("g", "generate", "Generate", priority=True),
        Binding("e", "embed", "Embed", priority=True),
        Binding("p", "pipeline", "Run All", priority=True),
        Binding("x", "stop", "Stop Tasks", priority=True),
        Binding("a", "articles", "Articles", priority=True),
        Binding("q", "quit", "Quit", priority=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        backend = config.ARTICLE_STORE_BACKEND
        backend_label = "Azure Blob" if backend == "azure" else "Local Disk"

        with Grid(id="app-grid"):
            with ScrollableContainer(id="sidebar"):
                yield Static("Actions", classes="stage-label")
                yield Button("Run Pipeline (All)", id="btn-pipeline", variant="primary")
                yield Button("Fetch Sources", id="btn-fetch")
                yield Button("Scrape Articles", id="btn-scrape")
                yield Button("Generate News", id="btn-generate")
                yield Button("Embed Articles", id="btn-embed")
                yield Button("Browse Articles", id="btn-articles", variant="success")
                yield Button("Stop Tasks (x)", id="btn-stop", variant="error")

                yield Static("\nStorage Backend", classes="stage-label")
                yield Button(f"Store: {backend_label}", id="btn-toggle-store", variant="warning" if backend == "azure" else "default")

                yield Static("\nSources (Click to Toggle)", classes="stage-label")
                with Vertical(id="sources-container"):
                    for name in SOURCE_REGISTRY.keys():
                        enabled = config.is_source_enabled(name)
                        label = f"{name}: {'[ON]' if enabled else '[OFF]'}"
                        variant = "success" if enabled else "default"
                        yield Button(label, id=f"btn-src-{name}", variant=variant)

            with ScrollableContainer(id="main-panel"):
                with Horizontal(classes="main-header-bar"):
                    yield Button("☰ Sidebar (b)", id="btn-toggle-sidebar")
                    yield Static(" Pipeline Status", classes="stage-label")
                yield Static("0 articles processed", id="article-count")

                with Vertical(classes="stage-panel"):
                    yield Static("Fetch Stage", classes="stage-label")
                    yield ProgressBar(id="pb-fetch", total=100, show_eta=False)
                    yield Static("", id="lbl-fetch-detail")

                with Vertical(classes="stage-panel"):
                    yield Static("Scrape Stage", classes="stage-label")
                    yield ProgressBar(id="pb-scrape", total=100, show_eta=False)
                    yield Static("", id="lbl-scrape-detail")

                with Vertical(classes="stage-panel"):
                    yield Static("Generate Stage", classes="stage-label")
                    yield ProgressBar(id="pb-generate", total=100, show_eta=False)
                    yield Static("", id="lbl-generate-detail")

                with Vertical(classes="stage-panel"):
                    yield Static("Embed Stage", classes="stage-label")
                    yield ProgressBar(id="pb-embed", total=100, show_eta=False)
                    yield Static("", id="lbl-embed-detail")

            with Vertical(id="log-panel"):
                yield RichLog(id="main-log", highlight=True, markup=True)

        yield Footer()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._is_quitting = False

    def on_mount(self) -> None:
        Logger.add_listener(self._handle_log)
        self._update_article_count()

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
        }
        color = colors.get(badge.upper(), "#c9d1d9")
        timestamp = time.strftime("%H:%M:%S")

        formatted_message = f"[dim]{timestamp}[/dim] [{color}][bold][{badge.upper()}][/{color}][/bold] {escape(message)}"
        if detail:
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
            from config import config
            article_store = create_article_store()
            articles = article_store.list_articles()
            count = len(articles)
            backend_label = "Azure Blob" if config.ARTICLE_STORE_BACKEND == "azure" else "Local Disk"
            lbl = self.query_one("#article-count", Static)
            text = f"{count} articles processed [{backend_label}]"
            self.call_from_thread(lbl.update, text)
        except Exception:
            pass

    def _handle_event(self, event: PipelineEvent) -> None:
        if self._is_quitting:
            return
        if isinstance(event, StageStarted):
            pb_id = f"#pb-{event.stage}"
            lbl_id = f"#lbl-{event.stage}-detail"
            try:
                pb = self.query_one(pb_id, ProgressBar)
                pb.update(total=event.total if event.total and event.total > 0 else 100, progress=0)
                lbl = self.query_one(lbl_id, Static)
                lbl.update(f"Starting {event.stage} stage...")
            except Exception:
                pass

        elif isinstance(event, StageProgress):
            pb_id = f"#pb-{event.stage}"
            lbl_id = f"#lbl-{event.stage}-detail"
            try:
                pb = self.query_one(pb_id, ProgressBar)
                if event.total and event.total > 0:
                    pb.update(total=event.total, progress=event.current)
                    pct = int((event.current / event.total) * 100)
                    progress_label = f"[{event.current}/{event.total}] ({pct}%) {escape(event.detail)}"
                else:
                    pb.update(progress=event.current)
                    progress_label = f"[{event.current}] {escape(event.detail)}"

                lbl = self.query_one(lbl_id, Static)
                lbl.update(progress_label)
            except Exception:
                pass

        elif isinstance(event, StageCompleted):
            pb_id = f"#pb-{event.stage}"
            lbl_id = f"#lbl-{event.stage}-detail"
            try:
                pb = self.query_one(pb_id, ProgressBar)
                pb.update(progress=pb.total)

                lbl = self.query_one(lbl_id, Static)
                lbl.update(f"✓ {event.stage.capitalize()} stage complete")

                if event.stage == "generate":
                    self._update_article_count()
            except Exception:
                pass

        elif isinstance(event, LogEvent):
            self._handle_log(event.badge, event.message, event.detail)

    def _run_pipeline(self, method_name: str) -> None:
        self.workers.cancel_group(self, "pipeline")

        def _emit_event(e: PipelineEvent) -> None:
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
                    self._is_quitting
                    or getattr(self, "_unmounted", False)
                    or (worker is not None and worker.is_cancelled)
                )

            runner = PipelineRunner(callback=_emit_event, stop_checker=_should_stop)
            method = getattr(runner, method_name)
            method()

        self.run_worker(_run, thread=True, group="pipeline", name=method_name, exclusive=True)

    def action_fetch(self) -> None:
        self._run_pipeline("run_fetch")

    def action_scrape(self) -> None:
        self._run_pipeline("run_scrape")

    def action_generate(self) -> None:
        self._run_pipeline("run_generate")

    def action_embed(self) -> None:
        self._run_pipeline("run_embed")

    def action_pipeline(self) -> None:
        self._run_pipeline("run_all")

    def action_stop(self) -> None:
        self.workers.cancel_group(self, "pipeline")
        self.workers.cancel_all()
        for stage in ["fetch", "scrape", "generate", "embed"]:
            try:
                lbl = self.query_one(f"#lbl-{stage}-detail", Static)
                lbl.update("[dim]Cancelled[/dim]")
            except Exception:
                pass
        self._handle_log("WARN", "Stopped active pipeline tasks.", None)

    def action_articles(self) -> None:
        self.push_screen(ArticlesScreen())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id == "btn-toggle-sidebar":
            self.action_toggle_sidebar()
        elif button_id == "btn-pipeline":
            self.action_pipeline()
        elif button_id == "btn-fetch":
            self.action_fetch()
        elif button_id == "btn-scrape":
            self.action_scrape()
        elif button_id == "btn-generate":
            self.action_generate()
        elif button_id == "btn-embed":
            self.action_embed()
        elif button_id == "btn-stop":
            self.action_stop()
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
        elif button_id.startswith("btn-src-"):
            source_name = button_id.removeprefix("btn-src-")
            new_status = config.toggle_source(source_name)
            event.button.label = f"{source_name}: {'[ON]' if new_status else '[OFF]'}"
            event.button.variant = "success" if new_status else "default"
            status_str = "[green]ENABLED[/green]" if new_status else "[dim]DISABLED[/dim]"
            self._handle_log("INFO", f"Source '{source_name}' is now {status_str}", None)
