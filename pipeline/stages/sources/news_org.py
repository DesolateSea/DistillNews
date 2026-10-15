from pipeline.engine.stage import stage
from pipeline.engine.stream import RawArticle
from pipeline.engine.task import PipelineContext


@stage
def fetch_news_org(ctx: PipelineContext):
    """Fetch articles from NewsAPI.org."""
    from config import config as default_config
    cfg = ctx.config if (ctx and ctx.config is not None) else default_config
    if not cfg.is_stage_enabled('fetch') or not cfg.is_source_enabled('news_org'):
        return

    from pipeline.sources.news_org import NewsFetcher
    from pipeline.sources.config import NEWS_ORG_TOPICS

    try:
        fetcher = NewsFetcher()
    except (ValueError, Exception):
        return

    for topic, keyword in NEWS_ORG_TOPICS.items():
        try:
            result = fetcher.fetch_all_articles(topic=keyword)
        except Exception:
            continue
        for article in (result or {}).get('articles', []):
            article['_assured_news'] = True
            article['_prompt'] = 'news_from_html.prompt.md'
            yield RawArticle(
                source='news_org',
                payload=article,
                url=article.get('url', ''),
                title=article.get('title', ''),
            )
