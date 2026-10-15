from pipeline.engine.stage import stage
from pipeline.engine.stream import RawArticle
from pipeline.engine.task import PipelineContext


@stage
def fetch_core(ctx: PipelineContext):
    """Fetch papers from Core API."""
    from config import config as default_config
    cfg = ctx.config if (ctx and ctx.config is not None) else default_config
    if not cfg.is_stage_enabled('fetch') or not cfg.is_source_enabled('core'):
        return

    import requests
    from pipeline.sources.config import CORE_KEYWORDS

    api_key = cfg.CORE_API_KEY
    if not api_key:
        return

    for keyword in CORE_KEYWORDS:
        if ctx and ctx.is_stopped():
            return
        try:
            r = requests.get(
                f'https://api.core.ac.uk/v3/search/works?q={keyword}&limit=20',
                headers={'Authorization': 'Bearer ' + api_key},
                timeout=5,
            )
            results = r.json().get('results', [])
        except Exception:
            continue
        for paper in results:
            if ctx and ctx.is_stopped():
                return
            item = {
                'content': paper.get('fullText', ''),
                'title': paper.get('title', ''),
                'citationCount': paper.get('citationCount', 0),
                '_assured_news': True,
                '_prompt': 'news_from_html.prompt.md',
            }
            yield RawArticle(
                source='core',
                payload=item,
                title=paper.get('title', ''),
            )
