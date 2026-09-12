"""
Persist stage — saves the finalized article to the article store.
"""

from pipeline.engine.stage import stage
from pipeline.engine.task import DropArticle, PipelineContext


@stage
def persist(embed: dict, ctx: PipelineContext) -> dict:
    """Save the processed article to the configured article store.

    Uses the article_id computed by the dedup stage.
    """
    if ctx.article_store is None:
        raise DropArticle('No article store configured')

    article_id = embed.get('_article_id')

    # Clean internal pipeline metadata before persisting
    clean = {k: v for k, v in embed.items() if not k.startswith('_')}

    saved_id = ctx.article_store.save_article(clean, article_id=article_id)
    clean['id'] = saved_id
    return clean
