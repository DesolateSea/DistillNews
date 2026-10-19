"""Custom News source stage — accepts direct input articles (text, files, or in-memory items).

Allows users and scripts to feed arbitrary news content directly into the
DistillNews streaming DAG pipeline for extraction and media bias analysis.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterator

from config import config as default_config
from pipeline.engine.stage import stage
from pipeline.engine.stream import RawArticle
from pipeline.engine.task import PipelineContext

logger = logging.getLogger(__name__)


def read_custom_input_from_path(file_or_dir: str | Path) -> Iterator[dict]:
    """Read custom news articles from a text/markdown file, JSON file, or directory."""
    path = Path(file_or_dir)
    if not path.exists():
        logger.warning("Custom news path not found: %s", path)
        return

    if path.is_file():
        if path.suffix.lower() == ".json":
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict):
                        title = item.get("title", path.stem)
                        content = item.get("content") or item.get("text") or ""
                        if content:
                            yield {
                                "title": title,
                                "content": content,
                                "_assured_news": True,
                                "_prompt": "news_from_html.prompt.md",
                            }
        else:
            # Plain text or Markdown file
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().strip()
                if content:
                    lines = content.splitlines()
                    title = lines[0].lstrip("# ").strip() if lines else path.stem
                    yield {
                        "title": title,
                        "content": content,
                        "_assured_news": True,
                        "_prompt": "news_from_html.prompt.md",
                    }
    elif path.is_dir():
        for file in sorted(path.iterdir()):
            if file.is_file() and file.suffix.lower() in (".txt", ".md", ".json"):
                yield from read_custom_input_from_path(file)


@stage
def fetch_custom_news(ctx: PipelineContext):
    """Producer stage: yields direct-input news articles into the pipeline."""
    cfg = ctx.config if (ctx and ctx.config is not None) else default_config
    if cfg and not cfg.is_stage_enabled("fetch"):
        return
    if cfg and not cfg.is_source_enabled("custom_news"):
        return

    # 1. In-memory items from ctx.extra
    if ctx and ctx.extra:
        items = ctx.extra.get("custom_news_items")
        if items:
            for idx, item in enumerate(items, 1):
                if ctx.is_stopped():
                    return
                if isinstance(item, str):
                    title = f"Custom Article {idx}"
                    content = item.strip()
                elif isinstance(item, dict):
                    title = item.get("title") or f"Custom Article {idx}"
                    content = item.get("content") or item.get("text") or ""
                else:
                    continue

                if content:
                    yield RawArticle(
                        source="custom_news",
                        payload={
                            "title": title,
                            "content": content,
                            "_assured_news": True,
                            "_prompt": "news_from_html.prompt.md",
                        },
                        title=title,
                    )

        # In-memory single text/title from ctx.extra
        extra_text = ctx.extra.get("custom_news_text")
        if extra_text:
            extra_title = ctx.extra.get("custom_news_title", "Custom Direct News")
            yield RawArticle(
                source="custom_news",
                payload={
                    "title": extra_title,
                    "content": extra_text.strip(),
                    "_assured_news": True,
                    "_prompt": "news_from_html.prompt.md",
                },
                title=extra_title,
            )

    # 2. Direct text from config / env
    if cfg and cfg.CUSTOM_NEWS_TEXT:
        direct_text = cfg.CUSTOM_NEWS_TEXT.strip()
        direct_title = cfg.CUSTOM_NEWS_TITLE or "Custom Direct News"
        yield RawArticle(
            source="custom_news",
            payload={
                "title": direct_title,
                "content": direct_text,
                "_assured_news": True,
                "_prompt": "news_from_html.prompt.md",
            },
            title=direct_title,
        )

    # 3. Direct path from config / env or ctx.extra
    path = (ctx.extra.get("custom_news_path") if ctx and ctx.extra else None) or (cfg.CUSTOM_NEWS_PATH if cfg else None)
    if path:
        for record in read_custom_input_from_path(path):
            if ctx and ctx.is_stopped():
                return
            yield RawArticle(
                source="custom_news",
                payload=record,
                title=record.get("title", "Custom News"),
            )
