"""LLM-based media bias detector using structured function tool calls.

Uses NEWS_BIAS_DETECTION_TOOL to obtain structured, multi-dimensional
media bias assessments from an LLM agent provider (OpenAI, Foundry, Ollama).
Evaluates overall biasness score (0.0 to 1.0), types of bias, and who the narrative favors/opposes.
"""

from __future__ import annotations

import json
from typing import Any

from pipeline.extraction_schemas import NEWS_BIAS_DETECTION_TOOL
from service.agents.base import AgentMessage, AgentProvider


SYSTEM_PROMPT = """You are an expert, non-partisan media bias and journalistic integrity analyst.
Your task is to analyze news articles for multidimensional media bias rather than simple left/right dichotomy.

Evaluation Dimensions:

1. Biasness Score (0.0 to 1.0):
   - 0.0 - 0.2: Highly neutral, objective, balanced, and evidence-based reporting.
   - 0.2 - 0.4: Mild slant or subtle word choice, but generally fair and informative.
   - 0.4 - 0.7: Noticeable bias, one-sided framing, selective quotes, or emotional rhetoric.
   - 0.7 - 1.0: Severe bias, propagandistic, highly partisan, or deceptive omission.

2. Bias Types (select all that apply):
   - "political": Ideological slant favoring/opposing specific political parties, leaders, or policies.
   - "linguistic": Emotionally charged adjectives, dramatic verbs, subjective spin (e.g. "slammed", "radical").
   - "cognitive": Confirmation bias, halo effect, false balance, or anchoring narrative on unverified claims.
   - "commercial": Promotional spin favoring corporate interests, advertisers, or native advertising.
   - "geopolitical": Nationalistic favoritism or regional chauvinism.
   - "selection_omission": Cherry-picking favorable facts while systematically omitting key counter-evidence.
   - "demographic": Skew based on gender, race, religion, or socio-economic class.

3. Who it Favors:
   - Name the specific entity, organization, party, administration, corporation, or group that the article portrays favorably (or 'none / neutral' if balanced).

4. Who it Opposes:
   - Name the specific entity, group, or viewpoint that the article criticizes, discredits, or marginalizes (or 'none / neutral' if balanced).

5. Loaded Language:
   - Extract specific loaded words, adjectives, or phrases exhibiting bias.

6. Reasoning:
   - Provide a concise analytical explanation justifying the bias score, detected types, and framing choices.

You MUST call the submit_news_bias_analysis tool with your evaluation."""


VALID_BIAS_TYPES = {
    "political",
    "linguistic",
    "cognitive",
    "commercial",
    "geopolitical",
    "selection_omission",
    "demographic",
}


def analyze_article_bias_with_llm(
    article: dict[str, Any],
    agent: AgentProvider,
) -> dict[str, Any]:
    """Analyze article content for media bias using LLM tool calling.

    Args:
        article: Article dictionary containing title, content/summary.
        agent: Initialized AgentProvider instance with tool calling support.

    Returns:
        Structured dictionary matching NEWS_BIAS_DETECTION_TOOL parameters,
        augmented with method="llm" metadata.
    """
    title = article.get("title", "").strip()
    content = (
        article.get("content")
        or article.get("markdown_content")
        or article.get("summary")
        or ""
    ).strip()

    if not title and not content:
        return {
            "method": "llm",
            "bias_score": 0.0,
            "bias_types": [],
            "who_it_favors": "none / neutral",
            "who_it_opposes": "none / neutral",
            "loaded_language": [],
            "reasoning": "Empty article content; cannot evaluate bias.",
        }

    user_text = f"Title: {title}\n\nContent:\n{content}"

    # Truncate to reasonable context window if article is excessively large
    if len(user_text) > 12000:
        user_text = user_text[:12000] + "\n\n[... content truncated for bias analysis ...]"

    messages = [
        AgentMessage(role="system", content=SYSTEM_PROMPT),
        AgentMessage(role="user", content=f"Please analyze the media bias of this news article:\n\n{user_text}"),
    ]

    tool_choice = {
        "type": "function",
        "function": {"name": NEWS_BIAS_DETECTION_TOOL.name},
    }

    try:
        response_msg = agent.chat_with_tools(
            messages=messages,
            tools=[NEWS_BIAS_DETECTION_TOOL],
            tool_choice=tool_choice,
        )
    except Exception as e:
        return _fallback_completion_analysis(article, agent, fallback_error=str(e))

    # Parse arguments from tool call
    if response_msg.tool_calls:
        for tool_call in response_msg.tool_calls:
            if tool_call.name == NEWS_BIAS_DETECTION_TOOL.name:
                args = tool_call.arguments
                if isinstance(args, dict):
                    return _normalize_tool_result(args)

    # If model responded with text instead of tool call, parse text
    if response_msg.content:
        return _extract_json_from_text(response_msg.content)

    return {
        "method": "llm",
        "bias_score": 0.0,
        "bias_types": [],
        "who_it_favors": "none / neutral",
        "who_it_opposes": "none / neutral",
        "loaded_language": [],
        "reasoning": "No response received from agent.",
    }


def _normalize_tool_result(args: dict[str, Any]) -> dict[str, Any]:
    """Ensure result contains all required fields with proper types and valid bounds."""
    try:
        score = float(args.get("bias_score", 0.0))
        score = max(0.0, min(1.0, score))
    except (TypeError, ValueError):
        score = 0.0

    raw_types = args.get("bias_types", [])
    if isinstance(raw_types, str):
        raw_types = [raw_types]
    elif not isinstance(raw_types, list):
        raw_types = []

    bias_types = []
    for t in raw_types:
        t_clean = str(t).strip().lower()
        if t_clean in VALID_BIAS_TYPES and t_clean not in bias_types:
            bias_types.append(t_clean)

    who_it_favors = str(args.get("who_it_favors", "none / neutral")).strip() or "none / neutral"
    who_it_opposes = str(args.get("who_it_opposes", "none / neutral")).strip() or "none / neutral"

    loaded = args.get("loaded_language", [])
    if isinstance(loaded, str):
        loaded = [loaded]
    elif not isinstance(loaded, list):
        loaded = []

    reasoning = str(args.get("reasoning", "")).strip()

    return {
        "method": "llm",
        "bias_score": round(score, 3),
        "bias_types": bias_types,
        "who_it_favors": who_it_favors,
        "who_it_opposes": who_it_opposes,
        "loaded_language": loaded,
        "reasoning": reasoning,
    }


def _extract_json_from_text(text: str) -> dict[str, Any]:
    """Attempt to extract structured bias JSON from raw text response."""
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, dict):
                return _normalize_tool_result(parsed)
    except Exception:
        pass

    return {
        "method": "llm",
        "bias_score": 0.0,
        "bias_types": [],
        "who_it_favors": "none / neutral",
        "who_it_opposes": "none / neutral",
        "loaded_language": [],
        "reasoning": text[:500],
    }


def _fallback_completion_analysis(
    article: dict[str, Any],
    agent: AgentProvider,
    fallback_error: str = "",
) -> dict[str, Any]:
    """Fallback when chat_with_tools is unavailable or errors out."""
    title = article.get("title", "")
    content = article.get("content") or article.get("summary") or ""
    prompt = f"""Analyze the media bias of this article. Return a JSON object with:
{{
  "bias_score": number between 0.0 (neutral) and 1.0 (biased),
  "bias_types": ["political", "linguistic", "cognitive", "commercial", "geopolitical", "selection_omission", "demographic"],
  "who_it_favors": "name of entity or 'none / neutral'",
  "who_it_opposes": "name of entity or 'none / neutral'",
  "loaded_language": ["word1", "word2"],
  "reasoning": "detailed explanation"
}}

Article Title: {title}
Article Content: {content[:3000]}"""

    try:
        res = agent.complete(SYSTEM_PROMPT, prompt)
        parsed = _extract_json_from_text(res.content)
        if fallback_error:
            parsed["_fallback_notice"] = f"Tool calling failed ({fallback_error}), used prompt completion"
        return parsed
    except Exception as e:
        return {
            "method": "llm",
            "bias_score": 0.0,
            "bias_types": [],
            "who_it_favors": "none / neutral",
            "who_it_opposes": "none / neutral",
            "loaded_language": [],
            "reasoning": f"Analysis failed: {e}",
            "error": str(e),
        }
