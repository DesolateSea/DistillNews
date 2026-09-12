"""
Format stage — converts article content to clean Markdown.
"""

from pathlib import Path

from pipeline.engine.stage import stage
from pipeline.engine.task import PipelineContext


PROMPTS_DIR = Path(__file__).resolve().parent.parent / 'prompts'


@stage
def format_markdown(extract: dict, ctx: PipelineContext) -> dict:
    """Format article content as clean Markdown.

    Calls markdown_formatter.prompt.md on the extracted content.
    """
    content = extract.get('content', '')
    if not content:
        extract['markdown_content'] = ''
        return extract

    if ctx.agent is None:
        extract['markdown_content'] = content
        return extract

    result = ctx.agent.complete_from_template(
        PROMPTS_DIR / 'markdown_formatter.prompt.md',
        {'content': content},
    )

    formatted = result.content.replace('\n', '\\n')
    extract['markdown_content'] = formatted
    return extract
