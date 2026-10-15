"""
Classify stage — LLM gatekeeper for non-assured sources.

For sources like Reddit where content may not be newsworthy,
this stage calls the is_news prompt to filter out non-news.
Assured sources (GNews, MediaStack, etc.) pass through directly.
"""

from pathlib import Path

from pipeline.engine.stage import stage
from pipeline.engine.task import DropArticle, PipelineContext


PROMPTS_DIR = Path(__file__).resolve().parent.parent / 'prompts'


@stage
def classify(dedup: dict, ctx: PipelineContext) -> dict:
    """Classify whether article is newsworthy.

    Passes through if source is assured (GNews, RapidNews, etc.).
    Calls is_news.prompt.md for unassured sources (Reddit).
    """
    assured = dedup.get('_assured_news', True)
    if assured:
        return dedup

    # Call LLM classification
    if ctx.agent is None:
        # No agent available — pass through
        return dedup

    result = ctx.agent.complete_from_template(
        PROMPTS_DIR / 'is_news.prompt.md',
        dedup,
    )
    output = result.content.strip().lower()

    if output == 'true':
        return dedup
    elif output == 'false':
        raise DropArticle(f"Not a news post: {dedup.get('title', '')[:50]}")
    else:
        # Ambiguous response — drop to be safe
        raise DropArticle(f"Ambiguous is_news response: {output}")
