"""
Embed stage — generates L2-normalized vector embedding for a single article.
"""

import math

from pipeline.engine.stage import stage
from pipeline.engine.task import PipelineContext


def _normalize_vector(vec: list[float]) -> list[float]:
    """L2-normalize a vector."""
    if not vec:
        return []
    sq_sum = sum(x * x for x in vec)
    if sq_sum == 0:
        return vec
    norm = math.sqrt(sq_sum)
    return [x / norm for x in vec]


@stage
def embed(format_markdown: dict, ctx: PipelineContext) -> dict:
    """Generate a vector embedding for the article.

    Uses the embedding provider from context. Falls back to
    sentence_transformers if the configured provider is 'none'.
    """
    title = format_markdown.get('title', '')
    content = (
        format_markdown.get('content')
        or format_markdown.get('markdown_content')
        or format_markdown.get('summary')
        or ''
    )
    text_to_embed = f"{title}\n\n{content}".strip()

    if not text_to_embed:
        format_markdown['embedding'] = []
        return format_markdown

    # Get or create embedding provider
    provider = ctx.extra.get('embedding_provider')
    if provider is None:
        try:
            from pipeline.embeddings.factory import create_embedding_provider
            from config import config
            target = config.EMBEDDING_PROVIDER
            if target.lower() == 'none':
                target = 'sentence_transformers'
            provider = create_embedding_provider(provider=target)
            ctx.extra['embedding_provider'] = provider
        except Exception:
            format_markdown['embedding'] = []
            return format_markdown

    try:
        vectors = provider.embed_many([text_to_embed])
        if vectors and vectors[0]:
            format_markdown['embedding'] = _normalize_vector(vectors[0])
        else:
            format_markdown['embedding'] = []
    except Exception:
        format_markdown['embedding'] = []

    return format_markdown
