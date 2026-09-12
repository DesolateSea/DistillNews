from pipeline.engine.stage import stage
from pipeline.engine.stream import RawArticle
from pipeline.engine.task import PipelineContext


@stage
def scrape_targets(ctx: PipelineContext):
    """Yield target URLs for web scraping."""
    from config import config as default_config
    cfg = ctx.config if (ctx and ctx.config is not None) else default_config
    if not cfg.is_stage_enabled('scrape') or not cfg.is_source_enabled('scrape'):
        return

    from service.db import FileStore
    from pipeline.scrapers.config import TARGET_URLS_JSON

    targets = FileStore.read_json(TARGET_URLS_JSON)
    if not targets:
        return

    for category, urls in targets.items():
        if ctx and ctx.is_stopped():
            return
        for url in urls:
            if ctx and ctx.is_stopped():
                return
            yield RawArticle(
                source='scrape',
                payload={
                    'url': url,
                    'category': category,
                    '_assured_news': True,
                    '_prompt': 'news_from_html.prompt.md',
                },
                url=url,
            )
