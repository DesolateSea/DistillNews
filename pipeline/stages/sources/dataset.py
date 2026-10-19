"""Dataset source stage — streams articles from offline benchmark datasets (CSV / JSONL).

Used for evaluating media bias benchmarks such as AllSides or BABE,
supporting both LLM agent and BERT model evaluations.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Iterator

from config import config as default_config
from pipeline.engine.stage import stage
from pipeline.engine.stream import RawArticle
from pipeline.engine.task import PipelineContext

logger = logging.getLogger(__name__)


def _extract_field(row: dict, candidates: list[str], default: str = "") -> str:
    """Extract first matching non-empty string field from row dictionary."""
    for cand in candidates:
        val = row.get(cand)
        if val is not None and str(val).strip():
            return str(val).strip()
    return default


def load_dataset_records(file_path: str | Path, limit: int | None = None) -> Iterator[dict]:
    """Read structured article records from a CSV, JSONL, or JSON dataset file.

    Args:
        file_path: Path to dataset file.
        limit: Optional maximum number of records to read.

    Yields:
        Parsed record dictionary with title, content, ground_truth, etc.
    """
    path = Path(file_path)
    if not path.is_file():
        logger.warning("Dataset file not found: %s", path)
        return

    count = 0
    content_keys = ["content", "text", "article", "body", "statement", "sentence"]
    title_keys = ["title", "headline", "name"]
    label_keys = ["label", "bias_rating", "bias", "ground_truth", "class", "target"]

    if path.suffix.lower() == ".csv":
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                content = _extract_field(row, content_keys)
                if not content:
                    continue

                title = _extract_field(row, title_keys)
                if not title:
                    title = content[:60].replace("\n", " ").strip() + "..."

                ground_truth = _extract_field(row, label_keys) or None
                url = _extract_field(row, ["url", "link"])
                pub_date = _extract_field(row, ["publication_date", "date"])

                record = {
                    "title": title,
                    "content": content,
                    "url": url,
                    "publication_date": pub_date,
                    "ground_truth": ground_truth,
                    "_assured_news": True,
                    "_prompt": "news_from_html.prompt.md",
                }
                yield record
                count += 1
                if limit is not None and count >= limit:
                    break

    elif path.suffix.lower() in (".jsonl", ".json"):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            if path.suffix.lower() == ".json":
                try:
                    data = json.load(f)
                    items = data if isinstance(data, list) else [data]
                except Exception as e:
                    logger.error("Failed to parse JSON file %s: %e", path, e)
                    return
            else:
                items = (json.loads(line) for line in f if line.strip())

            for row in items:
                if not isinstance(row, dict):
                    continue
                content = _extract_field(row, content_keys)
                if not content:
                    continue

                title = _extract_field(row, title_keys)
                if not title:
                    title = content[:60].replace("\n", " ").strip() + "..."

                ground_truth = _extract_field(row, label_keys) or None
                url = _extract_field(row, ["url", "link"])
                pub_date = _extract_field(row, ["publication_date", "date"])

                record = {
                    "title": title,
                    "content": content,
                    "url": url,
                    "publication_date": pub_date,
                    "ground_truth": ground_truth,
                    "_assured_news": True,
                    "_prompt": "news_from_html.prompt.md",
                }
                yield record
                count += 1
                if limit is not None and count >= limit:
                    break


@stage
def fetch_dataset(ctx: PipelineContext):
    """Producer stage: stream articles from configured benchmark dataset file."""
    cfg = ctx.config if (ctx and ctx.config is not None) else default_config
    if not cfg.is_stage_enabled("fetch") or not cfg.is_source_enabled("dataset"):
        return

    # Check context extra first, then config
    dataset_path = None
    limit = None
    if ctx and ctx.extra:
        dataset_path = ctx.extra.get("dataset_path")
        limit = ctx.extra.get("limit")

    if not dataset_path and cfg:
        dataset_path = cfg.DATASET_SOURCE_PATH

    if not dataset_path:
        logger.debug("fetch_dataset skipped: DATASET_SOURCE_PATH is not configured.")
        return

    for record in load_dataset_records(dataset_path, limit=limit):
        if ctx and ctx.is_stopped():
            return

        yield RawArticle(
            source="dataset",
            payload=record,
            title=record.get("title", ""),
        )
