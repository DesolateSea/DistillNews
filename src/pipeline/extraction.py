"""
News extraction pipeline.

Orchestrates the classification, extraction, and formatting of news articles
using an abstract agent provider. Provider is selected via the AGENT_PROVIDER
environment variable.

Replaces the old ``src/julep/run_extraction.py``.
"""

import json
import sys
from pathlib import Path
from hashlib import sha256

from agents import create_agent

from parsers.paragraph_extractor import clean_html
from parsers.reddit_parser import reddit_parser
from parsers.rapid_news_parser import rapid_news_parser
from parsers.media_stack_parser import media_stack_parser
from parsers.gnews_parser import gnews_parser

from pipeline.logger import log

# Resolve directories relative to src/
SRC_DIR = Path(__file__).resolve().parent.parent
prompts_dir = SRC_DIR / "prompts"
articles_dir = SRC_DIR / "data" / "processed"
test_dir = SRC_DIR / "tests" / "fixtures"

# Create a shared agent instance (provider selected by env var)
agent = create_agent()


def _get_article_path(input_data):
    """Compute target article JSON path from title and publication_date."""
    key = input_data["title"] + str(input_data["publication_date"])
    hashed_key = sha256(key.encode("utf-8")).hexdigest()
    return articles_dir / (hashed_key + ".json")


def _extract_news(input_data, prompt, source=None, debug=False, article_path=None):
    """
    Extract structured news from input data using an LLM agent.

    Args:
        input_data: dict with keys ``title``, ``publication_date``, ``content``
        prompt: YAML template filename under ``prompts_dir``
        source: optional source metadata
        debug: if True, print intermediate outputs
        article_path: optional pre-calculated Path to target JSON file
    """
    if article_path is None:
        article_path = _get_article_path(input_data)

    if article_path.exists():
        log.save_skip("Article already exists", str(article_path.resolve()))
        return None

    log.ai_call("extract_news", input_data["title"])
    result = agent.complete_from_template(prompts_dir / prompt, input_data)

    try:
        parsed = json.loads(result.content)
        parsed["source"] = source

        # Format content
        log.ai_call("format_markdown", input_data["title"])
        parsed["markdown_content"] = _format_news(parsed["content"], debug=debug)
        if parsed["markdown_content"] is None:
            log.warn("Failed to format markdown content", input_data["title"])

        string = json.dumps(parsed, indent=2)
        log.ai_result("format_markdown", "added markdown content")

    except Exception as e:
        log.error("JSON parse error in extraction", str(e))
        return None

    # Save structured output
    with open(article_path, "w", encoding="utf-8") as f:
        f.write(string)

    log.save(str(article_path.name), "Article saved")

    if debug:
        log.info("Structured output", string[:200])
    return parsed


def _is_news(input_data, prompt="is_news.yaml") -> bool | None:
    """Classify whether input is a newsworthy post."""
    log.ai_call("classify_is_news", input_data["title"])
    result = agent.complete_from_template(prompts_dir / prompt, input_data)

    output = result.content.strip().lower()
    is_news = None
    if output == "true":
        is_news = True
    elif output == "false":
        is_news = False

    log.ai_classify(input_data["title"], is_news)
    return is_news


def _format_news(content, prompt="markdown_formatter.yaml", debug=False) -> str | None:
    """Format plain-text news content as Markdown."""
    result = agent.complete_from_template(prompts_dir / prompt, {"content": content})

    formatted = result.content.replace("\n", "\\n")  # escape newlines
    if debug:
        log.info("Formatted output", formatted[:120])
    return formatted


def extract_news(obj, parser, prompt, assured_news=True, debug=False):
    """
    Full extraction pipeline for a single news item.

    1. Parse the raw object via ``parser``
    2. Check if article already exists on disk (BEFORE any AI calls)
    3. Optionally classify as news via LLM
    4. Extract structured data via LLM
    """
    log.divider()
    # Convert input to standard format
    log.parse_start(parser.__name__ if hasattr(parser, '__name__') else str(parser))
    formatted, source = parser(obj)
    if formatted is None:
        log.parse_fail("unknown", "parser returned None")
        return None

    # Article existence check BEFORE any AI calls
    article_path = _get_article_path(formatted)
    if article_path.exists():
        log.save_skip("Article already exists", str(article_path.resolve()))
        return None

    # Check if news or not (AI call)
    if not assured_news:
        is_news = _is_news(formatted)
        if is_news is None:
            return None
        if not is_news:
            log.save_skip("Not a news post", formatted.get("title", ""))
            return None

    # Generate article (AI call)
    article = _extract_news(formatted, prompt=prompt, source=source or obj, debug=debug, article_path=article_path)
    return article


# For debugging only
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m pipeline.extraction <source>")

    elif sys.argv[1] == "reddit":
        file = test_dir / "reddit.json"
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
        post = data[-2]
        extract_news(
            post,
            parser=reddit_parser,
            prompt="news_from_reddit_post.yaml",
            assured_news=False,
            debug=True,
        )

    elif sys.argv[1] == "rapid_news":
        file = test_dir / "rapid_news.json"
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
        news = data[0]
        extract_news(
            news,
            parser=rapid_news_parser,
            prompt="news_from_html_type1.yaml",
            debug=True,
        )

    elif sys.argv[1] == "media_stack":
        file = test_dir / "media_stack.json"
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
        news = data[0]
        extract_news(
            news,
            parser=media_stack_parser,
            prompt="news_from_html_type1.yaml",
            debug=True,
        )

    elif sys.argv[1] == "gnews":
        file = test_dir / "gnews.json"
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
        news = data[0]
        extract_news(
            news,
            parser=gnews_parser,
            prompt="news_from_html_type1.yaml",
            debug=True,
        )

    else:
        extract_news(
            sys.argv[1],
            parser=clean_html,
            prompt="news_from_html_type1.yaml",
            debug=True,
        )
