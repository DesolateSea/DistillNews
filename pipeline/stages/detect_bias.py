"""
Detect Bias stage — evaluates news article for media bias using LLM or BERT.
"""

from __future__ import annotations

from typing import Any

from pipeline.bias.llm_detector import analyze_article_bias_with_llm
from pipeline.bias.bert_detector import analyze_article_bias_with_bert
from pipeline.engine.stage import stage
from pipeline.engine.task import PipelineContext


@stage
def detect_bias(format_markdown: dict[str, Any], ctx: PipelineContext) -> dict[str, Any]:
    """Analyze media bias for an article.

    Reads BIAS_DETECTION_MODE from config:
    - 'none': Passthrough unchanged.
    - 'llm': Calls LLM agent using NEWS_BIAS_DETECTION_TOOL.
    - 'bert': Calls BERT sequence classification model.
    """
    cfg = ctx.config if (ctx and ctx.config is not None) else None
    mode = getattr(cfg, "BIAS_DETECTION_MODE", "none") if cfg else "none"

    if mode == "none":
        return format_markdown

    if mode == "llm":
        if ctx and ctx.agent:
            format_markdown["bias_analysis"] = analyze_article_bias_with_llm(
                format_markdown, ctx.agent
            )
    elif mode == "bert":
        model_name = getattr(cfg, "BIAS_BERT_MODEL", "bucketresearch/politicalBiasBERT") if cfg else "bucketresearch/politicalBiasBERT"
        device = getattr(cfg, "SENTENCE_TRANSFORMERS_DEVICE", None) if cfg else None
        format_markdown["bias_analysis"] = analyze_article_bias_with_bert(
            format_markdown,
            model_name=model_name,
            device=device,
        )

    return format_markdown
