from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, RichLog, ProgressBar, Button
from textual.containers import Horizontal, Vertical, ScrollableContainer, Grid
from textual.binding import Binding

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
                
                yield Static("\nSources", classes="stage-label")
                with ScrollableContainer():
                    for name in SOURCE_REGISTRY.keys():
                        enabled = config.is_source_enabled(name)
                        status_class = "source-enabled" if enabled else "source-disabled"
                        status_text = "🟢 Enabled" if enabled else "⚫ Disabled"
                        yield Static(f"[{name}]\n{status_text}", classes=f"source-card {status_class}")

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

    def on_mount(self) -> None:
        Logger.add_listener(self._handle_log)
        self._update_article_count()

    def on_unmount(self) -> None:
        Logger.remove_listener(self._handle_log)

    def _handle_log(self, badge: str, message: str, detail: str | None) -> None:
        log_widget = self.query_one("#main-log", RichLog)
        
        # Color mapping for badges
        badge_color = "#58a6ff"
        if badge == "ERROR":
            badge_color = "#f85149"
        elif badge == "WARN":
            badge_color = "#e3b341"
        elif badge == "SUCCESS":
            badge_color = "#3fb950"
            
        formatted_message = f"[[{badge_color}]{badge}[/]] {message}"
        if detail:
            formatted_message += f"\n  [dim]{detail}[/]"
            
        self.call_from_thread(log_widget.write, formatted_message)

    def _update_article_count(self) -> None:
        try:
            count = len(FileStore.list_processed_files())
            lbl = self.query_one("#article-count", Static)
            lbl.update(f"{count} articles processed")
        except Exception:
            pass

    def _handle_event(self, event: PipelineEvent) -> None:
        if isinstance(event, StageStarted):
            pb_id = f"#pb-{event.stage}"
            try:
                pb = self.query_one(pb_id, ProgressBar)
                pb.update(total=event.total, progress=0)
            except Exception:
                pass

        elif isinstance(event, StageProgress):
            pb_id = f"#pb-{event.stage}"
            lbl_id = f"#lbl-{event.stage}-detail"
            try:
                pb = self.query_one(pb_id, ProgressBar)
                pb.update(progress=event.current)
                
                lbl = self.query_one(lbl_id, Static)
                lbl.update(event.detail)
            except Exception:
                pass

        elif isinstance(event, StageCompleted):
            pb_id = f"#pb-{event.stage}"
            lbl_id = f"#lbl-{event.stage}-detail"
            try:
                pb = self.query_one(pb_id, ProgressBar)
                pb.update(progress=pb.total)
                
                lbl = self.query_one(lbl_id, Static)
                lbl.update(f"{event.stage.capitalize()} completed.")
                
                if event.stage == "generate":
                    self._update_article_count()
            except Exception:
                pass
                
        elif isinstance(event, LogEvent):
            self._handle_log(event.badge, event.message, event.detail)

    def _run_pipeline(self, method_name: str) -> None:
        def _run():
            runner = PipelineRunner(callback=lambda e: self.call_from_thread(self._handle_event, e))
            method = getattr(runner, method_name)
            method()
        self.run_worker(_run, thread=True)

    def action_fetch(self) -> None:
        self._run_pipeline("run_fetch")

    def action_scrape(self) -> None:
        self._run_pipeline("run_scrape")

    def action_generate(self) -> None:
        self._run_pipeline("run_generate")

    def action_pipeline(self) -> None:
        self._run_pipeline("run_all")

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
        elif event.button.id == "btn-articles":
            self.action_articles()
