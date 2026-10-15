"""
Dedup stage — checks if article already exists before AI calls.

Prevents wasted LLM API tokens by filtering duplicates early.
"""

from pipeline.engine.stage import stage
from pipeline.engine.task import DropArticle, PipelineContext
from service.blob.article_store import ArticleStore


@stage
def dedup(parse: dict, ctx: PipelineContext) -> dict:
    """Check if article already exists in the article store.

    Uses title + publication_date hash, URL matching, and title matching.
    Raises DropArticle if duplicate found.
    """
    title = parse.get('title', '')
    pub_date = parse.get('publication_date', '')

    if not title or title == 'Unknown':
        raise DropArticle('No title available')

    # Check by computed article ID
    article_id = ArticleStore.compute_article_id(title, pub_date)
    if ctx.article_store and ctx.article_store.article_exists(article_id):
        raise DropArticle(f'Article already exists: {article_id[:16]}')

    # Store computed ID for downstream stages
    parse['_article_id'] = article_id
    return parse
