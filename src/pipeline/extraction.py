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

# Resolve directories relative to src/
SRC_DIR = Path(__file__).resolve().parent.parent
prompts_dir = SRC_DIR / "prompts"
articles_dir = SRC_DIR / "data" / "processed"
test_dir = SRC_DIR / "tests" / "fixtures"

# Create a shared agent instance (provider selected by env var)
agent = create_agent()


def _extract_news(input_data, prompt, source=None, debug=False):
    """
    Extract structured news from input data using an LLM agent.

    Args:
        input_data: dict with keys ``title``, ``publication_date``, ``content``
        prompt: YAML template filename under ``prompts_dir``
        source: optional source metadata
        debug: if True, print intermediate outputs
    """
    key = input_data["title"] + str(input_data["publication_date"])
    hashed_key = sha256(key.encode("utf-8")).hexdigest()
    article_path = articles_dir / (hashed_key + ".json")

    if article_path.exists():
        print(f"Article already exists: {article_path}")
        return None

    print(f"Executing task for: {input_data['title']}")
    result = agent.complete_from_template(prompts_dir / prompt, input_data)

    try:
        parsed = json.loads(result.content)
        parsed["source"] = source

        # Format content
        parsed["markdown_content"] = _format_news(parsed["content"], debug=debug)
        if parsed["markdown_content"] is None:
            print("Exception: Failed to format content")

        string = json.dumps(parsed, indent=2)
        print("Added markdown content\n")

    except Exception as e:
        print("Error parsing JSON")
        print("Error:", e)
        print("Input:", result.content)
        return None

    # Save structured output
    with open(article_path, "w", encoding="utf-8") as f:
        f.write(string)

    if debug:
        print("Structured Output:\n", string)
    return parsed


def _is_news(input_data, prompt="is_news.yaml") -> bool | None:
    """Classify whether input is a newsworthy post."""
    print(f"Executing is_news task for: {input_data['title']}")
    result = agent.complete_from_template(prompts_dir / prompt, input_data)

    output = result.content.strip().lower()
    print("Classifier Output (news or not?):\n", output)

    if output not in ["true", "false"]:
        print("Invalid output")
        return None
    return output == "true"


def _format_news(content, prompt="markdown_formatter.yaml", debug=False) -> str | None:
    """Format plain-text news content as Markdown."""
    print("Formatting...")
    if debug:
        print(f"Executing formatting task for: {content}")

    result = agent.complete_from_template(prompts_dir / prompt, {"content": content})

    formatted = result.content.replace("\n", "\\n")  # escape newlines
    if debug:
        print("Formatted Output:\n", formatted)
    return formatted


def extract_news(obj, parser, prompt, assured_news=True, debug=False):
    """
    Full extraction pipeline for a single news item.

    1. Parse the raw object via ``parser``
    2. Optionally classify as news
    3. Extract structured data via LLM
    """
    print("------------------------")
    # Convert input to standard format
    formatted, source = parser(obj)
    if formatted is None:
        return None

    # Check if news or not
    if not assured_news:
        is_news = _is_news(formatted)
        if is_news is None:
            return None
        if not is_news:
            print("\nNot a news post!")
            return None

    # Generate article
    article = _extract_news(formatted, prompt=prompt, source=source or obj, debug=debug)
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
