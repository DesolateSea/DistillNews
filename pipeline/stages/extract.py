"""
Extract stage — structured LLM extraction of article metadata.

Calls the appropriate extraction prompt to produce structured JSON
with title, summary, category, tags, and content.
"""

import json
from pathlib import Path

from pipeline.engine.stage import stage
from pipeline.engine.task import DropArticle, PipelineContext
from config import config


PROMPTS_DIR = Path(__file__).resolve().parent.parent / 'prompts'


@stage
def extract(classify: dict, ctx: PipelineContext) -> dict:
    """Extract structured article data using LLM.

    Uses the prompt specified by the producer stage (e.g. news_from_html
    or news_from_reddit_post).
    """
    if ctx.agent is None:
        raise DropArticle('No agent available for extraction')

    prompt_name = classify.get('_prompt', 'news_from_html.prompt.md')
    article_id = classify.get('_article_id', '')

    result = ctx.agent.complete_from_template(
        PROMPTS_DIR / prompt_name,
        classify,
    )

    try:
        parsed = json.loads(result.content)
    except (json.JSONDecodeError, Exception) as e:
        raise DropArticle(f"JSON parse error in extraction: {e}")

    # Enrich with metadata
    parsed['source'] = classify.get('_source_meta', classify)
    parsed['prompt_used'] = prompt_name
    parsed['agent_provider'] = getattr(ctx.agent, 'provider_name', config.AGENT_PROVIDER)
    parsed['_article_id'] = article_id

    return parsed
