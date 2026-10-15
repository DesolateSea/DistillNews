from pipeline.engine.stage import stage
from pipeline.engine.stream import RawArticle
from pipeline.engine.task import PipelineContext


@stage
def fetch_rapid_news(ctx: PipelineContext):
    """Fetch news from RapidAPI Real-Time News."""
    from config import config as default_config
    cfg = ctx.config if (ctx and ctx.config is not None) else default_config
    if not cfg.is_stage_enabled('fetch') or not cfg.is_source_enabled('rapid_news'):
        return

    from pipeline.sources.rapid_news import RapidNewsFetcher
    from pipeline.sources.config import RAPID_NEWS_SECTIONS

    try:
        fetcher = RapidNewsFetcher()
    except Exception:
        return

    for category in RAPID_NEWS_SECTIONS:
        try:
            data = fetcher.fetch_news(category)
        except Exception:
            continue
        if not data:
            continue
        for item in data.get('data', []):
            item['_assured_news'] = True
            item['_prompt'] = 'news_from_html.prompt.md'
            yield RawArticle(
                source='rapid_news',
                payload=item,
                url=item.get('link', ''),
                title=item.get('title', ''),
            )
