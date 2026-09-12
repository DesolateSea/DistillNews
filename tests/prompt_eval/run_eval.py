"""
Prompt Pipeline Test Run.

Renders all prompts at each pipeline stage (Classification, Extraction, Markdown Formatting)
against sample articles, and records the full prompts and LLM outputs without truncation.
Outputs multiline status cleanly with tqdm.

Usage:
    python -m tests.prompt_eval.run_eval --dry-run
    python -m tests.prompt_eval.run_eval --sample tests/prompt_eval/samples/tech.json
    python -m tests.prompt_eval.run_eval --sample business --output /path/to/report.md
"""

from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tqdm import tqdm

from service.agents.prompt import Prompt
from service.agents.factory import create_agent
from service.agents.base import AgentProvider, CompletionResult


PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "pipeline" / "prompts"
SAMPLES_DIR = Path(__file__).resolve().parent / "samples"
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def load_single_sample(filepath: Path) -> dict[str, Any]:
    """Load a single JSON sample file and attach its file path."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["_filepath"] = str(filepath.resolve())
    if "id" not in data:
        data["id"] = filepath.stem
    return data


def resolve_samples(sample_target: str | Path | None = None) -> list[dict[str, Any]]:
    """Dynamically resolve sample file(s) by direct path, filename, or substring."""
    if not sample_target:
        # Load all JSON files in SAMPLES_DIR
        return [load_single_sample(p) for p in sorted(SAMPLES_DIR.glob("*.json"))]

    target = Path(sample_target)

    # 1. Exact file path exists on disk
    if target.is_file():
        return [load_single_sample(target)]

    # 2. Directory exists on disk
    if target.is_dir():
        files = sorted(target.glob("*.json"))
        if files:
            return [load_single_sample(p) for p in files]

    # 3. Path relative to SAMPLES_DIR (e.g. "business.json" or "business")
    candidate_in_samples = SAMPLES_DIR / target.name
    if candidate_in_samples.is_file():
        return [load_single_sample(candidate_in_samples)]

    candidate_with_ext = SAMPLES_DIR / f"{target.name}.json"
    if candidate_with_ext.is_file():
        return [load_single_sample(candidate_with_ext)]

    # 4. Substring or stem match in SAMPLES_DIR
    matches = [
        p for p in sorted(SAMPLES_DIR.glob("*.json"))
        if target.name.lower() in p.stem.lower() or target.name.lower() in p.name.lower()
    ]
    if matches:
        return [load_single_sample(p) for p in matches]

    available = [p.name for p in sorted(SAMPLES_DIR.glob("*.json"))]
    raise FileNotFoundError(
        f"Sample '{sample_target}' could not be resolved.\n"
        f"Available samples in {SAMPLES_DIR.name}/: {', '.join(available)}"
    )


# Alias for backward compatibility
load_samples = resolve_samples


def run_prompt_evaluation(
    agent: AgentProvider | None = None,
    dry_run: bool = False,
    output_report_path: Path | None = None,
    sample_target: str | Path | None = None,
    show_progress: bool = True,
) -> dict[str, Any]:
    """Run prompt test on each pipeline stage for the resolved samples."""
    samples = resolve_samples(sample_target)
    if not samples:
        raise RuntimeError(f"No sample files found in {SAMPLES_DIR}")

    try:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    report_lines: list[str] = []
    report_lines.append("# Prompt Pipeline Test Run\n")
    report_lines.append(f"**Generated**: {datetime.now(timezone.utc).isoformat()}  ")
    report_lines.append(f"**Mode**: {'Dry Run (Prompts Only)' if dry_run else 'Live Execution'}  ")
    report_lines.append(f"**Total Samples**: {len(samples)}\n")
    report_lines.append("---\n")

    # Load prompt templates
    is_news_prompt = Prompt(PROMPTS_DIR / "is_news.prompt.md")
    html_extract_prompt = Prompt(PROMPTS_DIR / "news_from_html.prompt.md")
    reddit_extract_prompt = Prompt(PROMPTS_DIR / "news_from_reddit_post.prompt.md")
    markdown_prompt = Prompt(PROMPTS_DIR / "markdown_formatter.prompt.md")

    run_results = {
        "total": len(samples),
        "samples": [],
    }

    if show_progress:
        print(f"\nRunning prompt pipeline tests ({len(samples)} sample{'s' if len(samples) > 1 else ''})...\n")

    pbar = tqdm(
        samples,
        desc="Overall Progress",
        unit="sample",
        disable=not show_progress,
        dynamic_ncols=True,
    )

    for sample in pbar:
        sample_id = sample.get("id", Path(sample["_filepath"]).stem)
        sample_title = sample.get("title", "N/A")
        expected_type = sample.get("expected_type", "news")

        if show_progress:
            tqdm.write(f"\n==================================================")
            tqdm.write(f"Sample: {sample_id} ({expected_type})")
            tqdm.write(f"Title:  {sample_title}")
            tqdm.write(f"==================================================")

        report_lines.append(f"## Sample: `{sample_id}`\n")
        report_lines.append(f"- **Title**: {sample_title}")
        report_lines.append(f"- **Expected Type**: {expected_type}")
        report_lines.append(f"- **File**: `{sample.get('_filepath', '')}`\n")

        # -------------------------------------------------------------
        # Stage 1: Classification (is_news)
        # -------------------------------------------------------------
        if show_progress:
            tqdm.write("  → Stage 1: Classification (is_news.prompt.md)")

        stage1_prompt = is_news_prompt.fill(**sample)
        stage1_output = "[Dry run: LLM not called]"
        if not dry_run and agent:
            try:
                res1 = agent.complete(stage1_prompt.system, stage1_prompt.user)
                stage1_output = res1.content.strip()
            except Exception as e:
                stage1_output = f"[Error: {e}]"

        report_lines.append("### Stage 1: Classification (`is_news.prompt.md`)\n")
        report_lines.append("#### System Prompt\n")
        report_lines.append("```text")
        report_lines.append(stage1_prompt.system)
        report_lines.append("```\n")

        report_lines.append("#### User Prompt\n")
        report_lines.append("```text")
        report_lines.append(stage1_prompt.user)
        report_lines.append("```\n")

        report_lines.append("#### Output\n")
        report_lines.append("```text")
        report_lines.append(stage1_output)
        report_lines.append("```\n")

        # -------------------------------------------------------------
        # Stage 2: Structured Extraction (news_from_html / news_from_reddit_post)
        # -------------------------------------------------------------
        is_reddit = "reddit" in sample_id.lower()
        active_extract = reddit_extract_prompt if is_reddit else html_extract_prompt
        prompt_name = "news_from_reddit_post.prompt.md" if is_reddit else "news_from_html.prompt.md"

        if show_progress:
            tqdm.write(f"  → Stage 2: Structured Extraction ({prompt_name})")

        stage2_prompt = active_extract.fill(**sample)
        stage2_output = "[Dry run: LLM not called]"
        extracted_content = sample.get("content", "")

        if not dry_run and agent:
            try:
                res2 = agent.complete(stage2_prompt.system, stage2_prompt.user)
                stage2_output = res2.content.strip()
                try:
                    parsed = json.loads(stage2_output)
                    if parsed.get("content"):
                        extracted_content = parsed["content"]
                except Exception:
                    pass
            except Exception as e:
                stage2_output = f"[Error: {e}]"

        report_lines.append(f"### Stage 2: Structured Extraction (`{prompt_name}`)\n")
        report_lines.append("#### System Prompt\n")
        report_lines.append("```text")
        report_lines.append(stage2_prompt.system)
        report_lines.append("```\n")

        report_lines.append("#### User Prompt\n")
        report_lines.append("```text")
        report_lines.append(stage2_prompt.user)
        report_lines.append("```\n")

        report_lines.append("#### Output\n")
        report_lines.append("```json")
        report_lines.append(stage2_output)
        report_lines.append("```\n")

        # -------------------------------------------------------------
        # Stage 3: Markdown Formatting (markdown_formatter)
        # -------------------------------------------------------------
        if show_progress:
            tqdm.write("  → Stage 3: Markdown Formatting (markdown_formatter.prompt.md)")

        stage3_prompt = markdown_prompt.fill(NEWS=extracted_content)
        stage3_output = "[Dry run: LLM not called]"
        if not dry_run and agent:
            try:
                res3 = agent.complete(stage3_prompt.system, stage3_prompt.user)
                stage3_output = res3.content.strip()
            except Exception as e:
                stage3_output = f"[Error: {e}]"

        report_lines.append("### Stage 3: Markdown Formatting (`markdown_formatter.prompt.md`)\n")
        report_lines.append("#### System Prompt\n")
        report_lines.append("```text")
        report_lines.append(stage3_prompt.system)
        report_lines.append("```\n")

        report_lines.append("#### User Prompt\n")
        report_lines.append("```text")
        report_lines.append(stage3_prompt.user)
        report_lines.append("```\n")

        report_lines.append("#### Output\n")
        report_lines.append("```markdown")
        report_lines.append(stage3_output)
        report_lines.append("```\n")

        report_lines.append("---\n")

        run_results["samples"].append({
            "sample_id": sample_id,
            "stage1": {"prompt": stage1_prompt, "output": stage1_output},
            "stage2": {"prompt": stage2_prompt, "output": stage2_output},
            "stage3": {"prompt": stage3_prompt, "output": stage3_output},
        })

    report_content = "\n".join(report_lines)

    target_path = output_report_path or (RESULTS_DIR / "test_run_latest.md")
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        destination_msg = f"Report saved to: {target_path}"
    except OSError:
        fallback_path = Path("/tmp/test_run_latest.md")
        with open(fallback_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        destination_msg = f"Report saved to: {fallback_path}"

    if show_progress:
        tqdm.write(f"\n{destination_msg}")
        tqdm.write(f"Completed pipeline run for {len(samples)} sample(s).\n")
    else:
        print(destination_msg)

    return run_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DistillNews Prompt Pipeline Test Run")
    parser.add_argument("--dry-run", action="store_true", help="Render all prompt stages without LLM calls")
    parser.add_argument(
        "--sample", "-s",
        type=str,
        default=None,
        help="Dynamic sample target: file path, relative file in samples/, or name substring",
    )
    parser.add_argument("--no-progress", action="store_true", help="Disable tqdm progress bar and terminal logs")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Path to save output report")
    args = parser.parse_args()

    agent_instance = None
    dry_run = args.dry_run
    if not dry_run:
        try:
            agent_instance = create_agent()
        except Exception as e:
            print(f"Could not initialize default agent ({e}), switching to --dry-run mode.")
            dry_run = True

    show_pbar = not args.no_progress and sys.stdout.isatty()
    results = run_prompt_evaluation(
        agent=agent_instance,
        dry_run=dry_run,
        output_report_path=args.output,
        sample_target=args.sample,
        show_progress=show_pbar,
    )
