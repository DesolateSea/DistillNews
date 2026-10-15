from pipeline.engine.stage import stage
from pipeline.engine.stream import RawArticle
from pipeline.engine.task import PipelineContext


@stage
def fetch_media_stack(ctx: PipelineContext):
    """Fetch news from MediaStack API."""
    from config import config as default_config
    cfg = ctx.config if (ctx and ctx.config is not None) else default_config
    if not cfg.is_stage_enabled('fetch') or not cfg.is_source_enabled('media_stack'):
        return

    from pipeline.sources.media_stack import MediaStack
    from pipeline.sources.config import MEDIA_STACK_CATEGORIES

    try:
        client = MediaStack()
    except (ValueError, Exception):
        return

    for category in MEDIA_STACK_CATEGORIES:
        try:
            data = client.get_news(categories=category)
        except Exception:
            continue
        if not data:
            continue
        for item in data.get('data', []):
            item['_assured_news'] = True
            item['_prompt'] = 'news_from_html.prompt.md'
            yield RawArticle(
                source='media_stack',
                payload=item,
                url=item.get('url', ''),
                title=item.get('title', ''),
            )
