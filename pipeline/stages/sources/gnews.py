from pipeline.engine.stage import stage
from pipeline.engine.stream import RawArticle
from pipeline.engine.task import PipelineContext


@stage
def fetch_gnews(ctx: PipelineContext):
    """Fetch articles from GNews API."""
    from config import config as default_config
    cfg = ctx.config if (ctx and ctx.config is not None) else default_config
    if not cfg.is_stage_enabled('fetch') or not cfg.is_source_enabled('gnews'):
        return

    from pipeline.sources.gnews import GNewsClient
    from pipeline.sources.config import GNEWS_QUERIES

    try:
        client = GNewsClient()
    except (ValueError, Exception):
        return

    for query in GNEWS_QUERIES:
        try:
            articles = client.fetch_articles(query)
        except Exception:
            continue
        for article in (articles or []):
            article['_assured_news'] = True
            article['_prompt'] = 'news_from_html.prompt.md'
            yield RawArticle(
                source='gnews',
                payload=article,
                url=article.get('url', ''),
                title=article.get('title', ''),
            )
