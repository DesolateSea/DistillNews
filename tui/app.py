import os
import time
import threading
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, RichLog, ProgressBar, Button
from textual.containers import Horizontal, Vertical, ScrollableContainer, Grid
from textual.binding import Binding
from textual.worker import get_current_worker
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
from utils.logger import Logger
from db import FileStore
from config import config
from tui.screens.articles import ArticlesScreen


class Dashboard(Static):
    pass


class DistillNewsApp(App):
    TITLE = "DistillNews"
    CSS_PATH = "styles/app.tcss"

    BINDINGS = [
        Binding("f", "fetch", "Fetch", priority=True),
        Binding("s", "scrape", "Scrape", priority=True),
        Binding("g", "generate", "Generate", priority=True),
        Binding("p", "pipeline", "Run All", priority=True),
        Binding("x", "stop", "Stop Tasks", priority=True),
        Binding("a", "articles", "Articles", priority=True),
        Binding("q", "quit", "Quit", priority=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Grid(id="app-grid"):
            with Vertical(id="sidebar"):
                yield Static("Actions", classes="stage-label")
                yield Button("Run Pipeline (All)", id="btn-pipeline", variant="primary")
                yield Button("Fetch Sources", id="btn-fetch")
                yield Button("Scrape Articles", id="btn-scrape")
                yield Button("Generate News", id="btn-generate")
                yield Button("Browse Articles", id="btn-articles", variant="success")
                yield Button("Stop Tasks (x)", id="btn-stop", variant="error")
                
                yield Static("\nSources", classes="stage-label")
                with ScrollableContainer():
                    for name in SOURCE_REGISTRY.keys():
                        enabled = config.is_source_enabled(name)
                        status_class = "source-enabled" if enabled else "source-disabled"
                        status_text = "ON" if enabled else "OFF"
                        status_style_class = "source-status-on" if enabled else "source-status-off"
                        with Horizontal(classes=f"source-card {status_class}"):
                            yield Static(f"[bold]\\[{escape(name)}][/bold]", classes="source-name")
                            yield Static(status_text, classes=f"source-status {status_style_class}")

            with Vertical(id="main-panel"):
                yield Static("Pipeline Status", classes="stage-label")
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

        def _force_exit():
            time.sleep(0.3)
            os._exit(0)

        threading.Thread(target=_force_exit, daemon=True).start()

    def _handle_log(self, badge: str, message: str, detail: str | None) -> None:
        if self._is_quitting:
            return
        try:
            log_widget = self.query_one("#main-log", RichLog)
        except Exception:
            return
        
        # Color mapping for badges
        badge_color = "#58a6ff"
        if badge == "ERROR":
            badge_color = "#f85149"
        elif badge == "WARN":
            badge_color = "#e3b341"
        elif badge == "SUCCESS":
            badge_color = "#3fb950"
            
        formatted_message = f"[[{badge_color}]{badge}[/]] {escape(message)}"
        if detail:
            formatted_message += f"\n  [dim]{escape(detail)}[/]"
            
        if threading.get_ident() == self._thread_id:
            log_widget.write(formatted_message)
        else:
            try:
                self.call_from_thread(log_widget.write, formatted_message)
            except Exception:
                pass

    def _update_article_count(self) -> None:
        if self._is_quitting:
            return
        try:
            count = len(FileStore.list_processed_files())
            lbl = self.query_one("#article-count", Static)
            if threading.get_ident() == self._thread_id:
                lbl.update(f"{count} articles processed")
            else:
                self.call_from_thread(lbl.update, f"{count} articles processed")
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
                pb.update(total=event.total if event.total > 0 else 100, progress=0)
                lbl = self.query_one(lbl_id, Static)
                lbl.update(f"Starting {event.stage} stage...")
            except Exception:
                pass

        elif isinstance(event, StageProgress):
            pb_id = f"#pb-{event.stage}"
            lbl_id = f"#lbl-{event.stage}-detail"
            try:
                pb = self.query_one(pb_id, ProgressBar)
                if event.total > 0:
                    pb.update(total=event.total, progress=event.current)
                else:
                    pb.update(progress=event.current)
                
                lbl = self.query_one(lbl_id, Static)
                lbl.update(escape(event.detail))
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

    def action_pipeline(self) -> None:
        self._run_pipeline("run_all")

    def action_stop(self) -> None:
        self.workers.cancel_group(self, "pipeline")
        self.workers.cancel_all()
        for stage in ["fetch", "scrape", "generate"]:
            try:
                lbl = self.query_one(f"#lbl-{stage}-detail", Static)
                lbl.update("[dim]Cancelled[/dim]")
            except Exception:
                pass
        self._handle_log("WARN", "Stopped active pipeline tasks.", None)

    def action_articles(self) -> None:
        self.push_screen(ArticlesScreen())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-pipeline":
            self.action_pipeline()
        elif event.button.id == "btn-fetch":
            self.action_fetch()
        elif event.button.id == "btn-scrape":
            self.action_scrape()
        elif event.button.id == "btn-generate":
            self.action_generate()
        elif event.button.id == "btn-stop":
            self.action_stop()
        elif event.button.id == "btn-articles":
            self.action_articles()
