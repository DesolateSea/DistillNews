"""
Parse stage — dispatches raw items to source-specific parsers.

Runs concurrently in the worker thread pool. Heavy HTTP scraping
(e.g. fetching article bodies from URLs) happens here in parallel.
"""

from pipeline.engine.stage import stage
from pipeline.engine.stream import RawArticle
from pipeline.engine.task import DropArticle, PipelineContext

# Parser dispatch table — maps source name to (parser_func, needs_no_repeat)
PARSER_REGISTRY = {}


def _init_parsers():
    """Lazy-init parser registry to avoid import-time side effects."""
    global PARSER_REGISTRY
    if PARSER_REGISTRY:
        return
    from pipeline.parsers.reddit_parser import reddit_parser
    from pipeline.parsers.gnews_parser import gnews_parser
    from pipeline.parsers.rapid_news_parser import rapid_news_parser
    from pipeline.parsers.media_stack_parser import media_stack_parser
    from pipeline.parsers.paragraph_extractor import clean_html
    from pipeline.scrapers.scraper import scrape_target

    def scrape_parser(payload, no_repeat=False):
        """Parse a scrape target: fetch HTML then extract paragraphs."""
        url = payload.get('url', '')
        html = scrape_target(url)
        if not html:
            return None, None
        parsed, source = clean_html(html)
        if parsed:
            parsed['url'] = url
            parsed['category'] = payload.get('category', '')
        return parsed, source

    def core_parser(payload, no_repeat=False):
        """Passthrough parser for Core API items (already structured)."""
        return payload, payload

    PARSER_REGISTRY.update({
        'reddit': reddit_parser,
        'gnews': gnews_parser,
        'rapid_news': rapid_news_parser,
        'media_stack': media_stack_parser,
        'scrape': scrape_parser,
        'core': core_parser,
        'news_org': gnews_parser,  # NewsAPI uses same format as GNews
    })


@stage
def parse(raw_article: RawArticle, ctx: PipelineContext | None = None) -> dict:
    """Parse a raw article item into a standardized dict.

    Dispatches to the appropriate source-specific parser.
    Runs in the worker thread pool — HTTP scraping happens here.
    """
    if ctx and ctx.is_stopped():
        raise DropArticle("Pipeline cancelled")

    _init_parsers()

    source = raw_article.source
    parser = PARSER_REGISTRY.get(source)
    if parser is None:
        raise DropArticle(f"No parser registered for source: {source}")

    payload = raw_article.payload

    # Call parser with no_repeat=False (dedup is handled by the dedup stage)
    try:
        formatted, source_meta = parser(payload, no_repeat=False)
    except Exception as e:
        raise DropArticle(f"Parser error ({source}): {e}")

    if formatted is None:
        raise DropArticle(f"Parser returned None for {source}")

    # Carry forward pipeline metadata from producer
    if isinstance(payload, dict):
        formatted['_assured_news'] = payload.get('_assured_news', True)
        formatted['_prompt'] = payload.get('_prompt', 'news_from_html.prompt.md')
        formatted['_source_meta'] = source_meta

    return formatted
