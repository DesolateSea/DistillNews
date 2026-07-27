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

    def _is_stopped(self) -> bool:
        return bool(self.stop_checker and self.stop_checker())

    def _emit(self, event: PipelineEvent):
        if self._is_stopped():
            raise PipelineCancelled("Pipeline task was cancelled")
        if self.callback:
            self.callback(event)

    def run_all(self, sources: list[str] | None = None):
        if self._is_stopped():
            return
        self.run_fetch(sources=sources)
        if self._is_stopped():
            return
        self.run_scrape()
        if self._is_stopped():
            return
        self.run_generate()
        if self._is_stopped():
            return
        self.run_embed()

    def run_fetch(self, sources: list[str] | None = None):
        sources_to_run = sources if sources else list(SOURCE_REGISTRY.keys())
        self._emit(StageStarted(stage="fetch", total=len(sources_to_run)))
        
        current = 0
        from service.db import FileStore
        run_timestamp = FileStore.get_iso_timestamp()
        
        for source_name in sources_to_run:
            if self._is_stopped():
                break
            if not config.is_source_enabled(source_name):
                self._emit(LogEvent(badge="skip", message=f"Skipping {source_name}", detail="Source disabled"))
                continue
            
            if source_name not in SOURCE_REGISTRY:
                self._emit(LogEvent(badge="fail", message=f"Unknown source: {source_name}"))
                continue
            
            self._emit(LogEvent(badge="fetch", message=f"Starting fetch for {source_name}"))
            
            try:
                mod_name, func_name = SOURCE_REGISTRY[source_name]
                if mod_name == __name__:
                    func = globals()[func_name]
                else:
                    mod = importlib.import_module(mod_name)
                    func = getattr(mod, func_name)
                try:
                    func(run_timestamp=run_timestamp)
                except TypeError:
                    func()
            except PipelineCancelled:
                break
            except Exception as e:
                self._emit(LogEvent(badge="fail", message=f"Fetch failed for {source_name}", detail=str(e)))
                
            current += 1
            self._emit(StageProgress(stage="fetch", current=current, total=len(sources_to_run), detail=source_name))
            
        if not self._is_stopped():
            self._emit(StageCompleted(stage="fetch"))

    def run_scrape(self):
        if self._is_stopped():
            return
        try:
            from service.db import FileStore
            from pipeline.scrapers.config import TARGET_URLS_JSON
            targets = FileStore.read_json(TARGET_URLS_JSON)
            total = sum(len(urls) for urls in targets.values()) if targets else 1
        except Exception:
            total = 1

        self._emit(StageStarted(stage="scrape", total=total))
        run_timestamp = FileStore.get_iso_timestamp()

        def callback(cur, tot, detail):
            if self._is_stopped():
                raise PipelineCancelled()
            self._emit(StageProgress(stage="scrape", current=cur, total=tot, detail=detail))

        try:
            from pipeline.scrape import run_scrape as run_scrape_func
            run_scrape_func(progress_callback=callback, run_timestamp=run_timestamp)
            if not self._is_stopped():
                self._emit(StageCompleted(stage="scrape"))
        except PipelineCancelled:
            pass
        except Exception as e:
            self._emit(LogEvent(badge="fail", message="Scrape failed", detail=str(e)))

    def run_generate(self):
        if self._is_stopped():
            return
        self._emit(StageStarted(stage="generate", total=100))

        def _on_generate_progress(current: int, total: int, detail: str):
            if self._is_stopped():
                raise PipelineCancelled("Pipeline task was cancelled")
            self._emit(StageProgress(stage="generate", current=current, total=total, detail=detail))

        try:
            from pipeline.generate import generate_articles
            generate_articles(progress_callback=_on_generate_progress)
        except PipelineCancelled:
            pass
        except Exception as e:
            self._emit(LogEvent(badge="fail", message="Generate failed", detail=str(e)))

        if not self._is_stopped():
            self._emit(StageCompleted(stage="generate"))

    def run_embed(self):
        if self._is_stopped():
            return
        self._emit(StageStarted(stage="embed", total=100))

        def _on_embed_progress(current: int, total: int, detail: str):
            if self._is_stopped():
                raise PipelineCancelled("Pipeline task was cancelled")
            self._emit(StageProgress(stage="embed", current=current, total=total, detail=detail))

        try:
            from pipeline.embed import generate_embeddings
            generate_embeddings(progress_callback=_on_embed_progress)
        except PipelineCancelled:
            pass
        except Exception as e:
            self._emit(LogEvent(badge="fail", message="Embed failed", detail=str(e)))

        if not self._is_stopped():
            self._emit(StageCompleted(stage="embed"))
