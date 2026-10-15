from dataclasses import dataclass
from typing import Callable, Any
import importlib
import sys

from config import config


@dataclass
class PipelineEvent:
    pass


@dataclass
class StageStarted(PipelineEvent):
    stage: str
    total: int | None = None


@dataclass
class StageProgress(PipelineEvent):
    stage: str
    current: int
    total: int | None
    detail: str = ""


@dataclass
class StageCompleted(PipelineEvent):
    stage: str


@dataclass
class LogEvent(PipelineEvent):
    badge: str
    message: str
    detail: str | None = None


def _run_gnews():
    from pipeline.sources.gnews import GNewsClient
    from pipeline.sources.config import GNEWS_QUERIES
    client = GNewsClient()
    for query in GNEWS_QUERIES:
        client.fetch_articles(query)


def _run_rapid_news():
    from pipeline.sources.rapid_news import RapidNewsFetcher
    from pipeline.sources.config import RAPID_NEWS_SECTIONS
    fetcher = RapidNewsFetcher()
    for category in RAPID_NEWS_SECTIONS:
        data = fetcher.fetch_news(category)
        if data:
            fetcher.save_data(category, data)


def _run_media_stack():
    from pipeline.sources.media_stack import MediaStack
    from pipeline.sources.config import MEDIA_STACK_CATEGORIES
    client = MediaStack()
    for cat in MEDIA_STACK_CATEGORIES:
        data = client.get_news(categories=cat)
        if data:
            client.save_data(data, topic=cat)


def _run_news_org():
    from pipeline.sources.news_org import NewsFetcher
    from pipeline.sources.config import NEWS_ORG_TOPICS
    fetcher = NewsFetcher()
    for topic, keyword in NEWS_ORG_TOPICS.items():
        fetcher.fetch_all_articles(topic=keyword)


SOURCE_REGISTRY = {
    'reddit': ('pipeline.sources.reddit', 'run_reddit_ingestion'),
    'gnews': (__name__, '_run_gnews'),  # needs wrapper
    'rapid_news': (__name__, '_run_rapid_news'),  # needs wrapper  
    'media_stack': (__name__, '_run_media_stack'),  # needs wrapper
    'news_org': (__name__, '_run_news_org'),  # needs wrapper
    'core': ('pipeline.sources.core', 'run_core_fetch'),
}


class PipelineCancelled(Exception):
    pass


class PipelineRunner:
    def __init__(
        self,
        callback: Callable[[PipelineEvent], None] | None = None,
        stop_checker: Callable[[], bool] | None = None,
    ):
        self.callback = callback
        self.stop_checker = stop_checker
        self.current_streaming_runner = None

    def _is_stopped(self) -> bool:
        return bool(self.stop_checker and self.stop_checker())

    def stop(self) -> None:
        """Signal running engine to stop immediately."""
        if self.current_streaming_runner:
            try:
                self.current_streaming_runner.stop()
            except Exception:
                pass

    def _emit(self, event: PipelineEvent):
        if self._is_stopped():
            raise PipelineCancelled("Pipeline task was cancelled")
        if self.callback:
            self.callback(event)

    def run_streaming(self, sources: list[str] | None = None, max_workers: int = 10):
        """
        Execute the full pipeline using the streaming DAG task engine.
        Maps streaming TaskEvents into TUI/CLI PipelineEvents for live visual feedback.
        """
        if self._is_stopped():
            return

        from pipeline.engine.registry import StageRegistry
        from pipeline.engine.runner import StreamingRunner
        from pipeline.engine.task import PipelineContext, TaskState
        from service.agents.factory import create_agent
        from service.db import create_article_store

        # Ensure stages are loaded and registered
        import pipeline.stages

        reg = StageRegistry()
        reg.discover()

        # If fetch stage is disabled, remove all fetch producers
        if not config.is_stage_enabled("fetch"):
            for producer in list(reg.producers):
                if producer.name.startswith("fetch_"):
                    if producer.name in reg._stages:
                        del reg._stages[producer.name]

        # If scrape stage is disabled, remove scrape_targets
        if not config.is_stage_enabled("scrape"):
            if "scrape_targets" in reg._stages:
                del reg._stages["scrape_targets"]

        # Filter disabled sources from registry
        for producer in list(reg.producers):
            source_key = producer.name.removeprefix("fetch_").replace("scrape_targets", "scrape")
            if not config.is_source_enabled(source_key):
                if producer.name in reg._stages:
                    del reg._stages[producer.name]

        # If explicit sources are specified, filter producers
        if sources:
            source_stages = set()
            for s in sources:
                source_stages.add(f"fetch_{s}")
                if s == "scrape":
                    source_stages.add("scrape_targets")
            for producer in list(reg.producers):
                if producer.name not in source_stages and producer.name not in sources:
                    del reg._stages[producer.name]

        # Initialize shared context
        try:
            agent = create_agent()
        except Exception:
            agent = None

        try:
            article_store = create_article_store()
        except Exception:
            article_store = None

        ctx = PipelineContext(
            agent=agent,
            article_store=article_store,
            config=config,
            stop_checker=self._is_stopped,
        )

        # Notify TUI/listeners that stages have started
        self._emit(StageStarted(stage="fetch", total=100))
        self._emit(StageStarted(stage="scrape", total=100))
        self._emit(StageStarted(stage="generate", total=100))
        self._emit(StageStarted(stage="embed", total=100))

        stage_counts = {"fetch": 0, "scrape": 0, "generate": 0, "embed": 0}
        article_titles: dict[str, str] = {}

        def _on_task_event(event):
            if self._is_stopped():
                raise PipelineCancelled("Pipeline was cancelled")

            # Forward granular TaskEvent to callback
            self._emit(event)

            # Track article titles
            t = getattr(event, "article_title", "")
            if not t and isinstance(getattr(event, "result", None), dict):
                res_title = event.result.get("title")
                if res_title and str(res_title).strip().lower() != "unknown":
                    t = str(res_title).strip()
            if t:
                article_titles[event.article_id] = t

            title = article_titles.get(event.article_id, "")

            # Determine high-level stage mapping
            if event.stage_name.startswith("fetch_"):
                mapped = "fetch"
            elif event.stage_name == "scrape_targets":
                mapped = "scrape"
            elif event.stage_name == "embed":
                mapped = "embed"
            else:
                mapped = "generate"

            if event.state == TaskState.RUNNING:
                stage_counts[mapped] += 1
                if title:
                    t_short = title[:40] + "..." if len(title) > 40 else title
                    progress_detail = f"{event.stage_name}: {t_short}"
                else:
                    progress_detail = f"{event.stage_name} [{event.article_id[:8]}]"
                self._emit(
                    StageProgress(
                        stage=mapped,
                        current=stage_counts[mapped],
                        total=max(stage_counts[mapped] + 10, 100),
                        detail=progress_detail,
                    )
                )
            elif event.state == TaskState.DONE:
                if not event.article_id.startswith("__producer__"):
                    if title:
                        title_clean = title.strip()
                        if len(title_clean) > 80:
                            title_clean = title_clean[:77] + "..."
                        detail_text = f"\"{title_clean}\" ({event.article_id[:8]})"
                    else:
                        detail_text = event.article_id[:16]

                    self._emit(
                        LogEvent(
                            badge="done",
                            message=f"{event.stage_name} complete",
                            detail=detail_text,
                        )
                    )
            elif event.state == TaskState.DROPPED:
                detail_str = str(event.detail) if event.detail else "dropped"
                if title:
                    title_clean = title.strip()
                    if len(title_clean) > 60:
                        title_clean = title_clean[:57] + "..."
                    detail_text = f"{detail_str} — \"{title_clean}\" ({event.article_id[:8]})"
                else:
                    detail_text = f"{detail_str} ({event.article_id[:8]})"
                self._emit(
                    LogEvent(
                        badge="skip",
                        message=f"{event.stage_name}: dropped",
                        detail=detail_text,
                    )
                )
            elif event.state == TaskState.FAILED:
                detail_str = str(event.detail) if event.detail else "failed"
                if title:
                    title_clean = title.strip()
                    if len(title_clean) > 60:
                        title_clean = title_clean[:57] + "..."
                    detail_text = f"{detail_str} — \"{title_clean}\" ({event.article_id[:8]})"
                else:
                    detail_text = f"{detail_str} ({event.article_id[:8]})"
                self._emit(
                    LogEvent(
                        badge="fail",
                        message=f"{event.stage_name}: failed",
                        detail=detail_text,
                    )
                )

        runner = StreamingRunner(
            registry=reg,
            ctx=ctx,
            max_workers=max_workers,
            on_event=_on_task_event,
            stop_checker=self._is_stopped,
        )
        self.current_streaming_runner = runner

        try:
            runner.run()
        except PipelineCancelled:
            runner.stop()
            raise
        except Exception as e:
            self._emit(LogEvent(badge="fail", message="Pipeline error", detail=str(e)))
            raise
        finally:
            self.current_streaming_runner = None

        if not self._is_stopped():
            self._emit(StageCompleted(stage="fetch"))
            self._emit(StageCompleted(stage="scrape"))
            self._emit(StageCompleted(stage="generate"))
            self._emit(StageCompleted(stage="embed"))

    def run_all(self, sources: list[str] | None = None):
        """Execute the full streaming pipeline."""
        if self._is_stopped():
            return
        self.run_streaming(sources=sources)

    def run_fetch(self, sources: list[str] | None = None):
        """Execute streaming pipeline for fetch sources."""
        if self._is_stopped():
            return
        fetch_sources = sources if sources else [s for s in SOURCE_REGISTRY.keys() if s != "scrape"]
        self.run_streaming(sources=fetch_sources)

    def run_scrape(self):
        """Execute streaming pipeline for web scrape targets."""
        if self._is_stopped():
            return
        self.run_streaming(sources=["scrape"])

    def run_generate(self):
        """Execute streaming pipeline for all enabled sources through generation."""
        if self._is_stopped():
            return
        self.run_streaming()

    def run_embed(self, force: bool = False):
        """Generate and normalize vector embeddings for all unembedded articles."""
        if self._is_stopped():
            return
        self._emit(StageStarted(stage="embed", total=100))

        from service.db import create_article_store
        from pipeline.embeddings.factory import create_embedding_provider
        from pipeline.stages.embed import _normalize_vector

        target_provider = config.EMBEDDING_PROVIDER
        if target_provider.lower() == "none":
            target_provider = "sentence_transformers"

        try:
            provider = create_embedding_provider(provider=target_provider)
            store = create_article_store()
            articles = list(store.load_all_articles())
            should_force = force or config.FORCE_REEMBED

            queued = []
            for art in articles:
                has_emb = art.get("embedding") and isinstance(art["embedding"], list) and len(art["embedding"]) > 0
                if should_force or not has_emb:
                    t = art.get("title", "")
                    c = art.get("content") or art.get("markdown_content") or art.get("summary") or ""
                    text = f"{t}\n\n{c}".strip()
                    if text:
                        queued.append((art, text))

            total = len(queued)
            if total == 0:
                self._emit(LogEvent(badge="done", message="All articles already have embeddings"))
            else:
                batch_size = 32
                for i in range(0, total, batch_size):
                    if self._is_stopped():
                        raise PipelineCancelled()
                    batch = queued[i : i + batch_size]
                    vectors = provider.embed_many([txt for _, txt in batch])
                    for (art, _), vec in zip(batch, vectors):
                        if vec:
                            art["embedding"] = _normalize_vector(vec)
                            store.save_article(art, article_id=art.get("id"))
                    self._emit(
                        StageProgress(
                            stage="embed",
                            current=min(i + len(batch), total),
                            total=total,
                            detail=f"Batch {i // batch_size + 1}",
                        )
                    )

            if not self._is_stopped():
                self._emit(StageCompleted(stage="embed"))
        except PipelineCancelled:
            pass
        except Exception as e:
            self._emit(LogEvent(badge="fail", message="Embed failed", detail=str(e)))
