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


class PipelineRunner:
    def __init__(self, callback: Callable[[PipelineEvent], None] | None = None):
        self.callback = callback

    def _emit(self, event: PipelineEvent):
        if self.callback:
            self.callback(event)

    def run_all(self, sources: list[str] | None = None):
        self.run_fetch(sources=sources)
        self.run_scrape()
        self.run_generate()

    def run_fetch(self, sources: list[str] | None = None):
        sources_to_run = sources if sources else list(SOURCE_REGISTRY.keys())
        self._emit(StageStarted(stage="fetch", total=len(sources_to_run)))
        
        current = 0
        
        for source_name in sources_to_run:
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
                func()
            except Exception as e:
                self._emit(LogEvent(badge="fail", message=f"Fetch failed for {source_name}", detail=str(e)))
                
            current += 1
            self._emit(StageProgress(stage="fetch", current=current, total=len(sources_to_run), detail=source_name))
            
        self._emit(StageCompleted(stage="fetch"))

    def run_scrape(self):
        self._emit(StageStarted(stage="scrape"))
        try:
            from pipeline.scrape import run_scrape
            run_scrape()
        except Exception as e:
            self._emit(LogEvent(badge="fail", message="Scrape failed", detail=str(e)))
        self._emit(StageCompleted(stage="scrape"))
        
    def run_generate(self):
        self._emit(StageStarted(stage="generate"))
        try:
            from pipeline.generate import generate_articles
            generate_articles()
        except Exception as e:
            self._emit(LogEvent(badge="fail", message="Generate failed", detail=str(e)))
        self._emit(StageCompleted(stage="generate"))
