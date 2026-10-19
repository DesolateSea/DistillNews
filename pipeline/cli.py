#!/usr/bin/env python3
"""
DistillNews CLI — entry point for launching the interactive TUI dashboard.

Usage:
    python pipeline/cli.py              Launch the TUI dashboard (default)
    python pipeline/cli.py tui          Launch the TUI dashboard (explicit)

Options:
    --storage, -st [file|azure]         Override ARTICLE_STORE_BACKEND
"""

import os
import sys
from pathlib import Path

# Ensure the project root directory is on sys.path so project imports work
_root_dir = str(Path(__file__).resolve().parent.parent)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

import click


def _apply_storage(storage: str | None):
    if storage:
        os.environ["ARTICLE_STORE_BACKEND"] = storage.lower()


class ColoredGroup(click.Group):
    """Click Group that preserves formatting and ANSI colors in epilog."""

    def format_epilog(self, ctx, formatter):
        if self.epilog:
            formatter.write_paragraph()
            formatter.write(self.epilog)


class ColoredCommand(click.Command):
    """Click Command that preserves formatting and ANSI colors in epilog."""

    def format_epilog(self, ctx, formatter):
        if self.epilog:
            formatter.write_paragraph()
            formatter.write(self.epilog)


MAIN_HELP_EPILOG = f"""{click.style('Examples:', fg='bright_yellow', bold=True)}
  {click.style('1. Launch interactive Textual TUI dashboard:', fg='cyan', bold=True)}
     $ python pipeline/cli.py

  {click.style('2. Launch TUI dashboard with Azure Blob Storage backend:', fg='cyan', bold=True)}
     $ python pipeline/cli.py tui --storage azure

  {click.style('3. Direct news text analysis with multidimensional LLM detector:', fg='cyan', bold=True)}
     $ python pipeline/cli.py analyze --text "The legislation passed amid controversy."

  {click.style('4. Dynamic BERT stance classification with custom Hugging Face model:', fg='cyan', bold=True)}
     $ python pipeline/cli.py analyze --detector bert --model mediabiasgroup/roberta-babe-ft --text "..."

  {click.style('5. Batch evaluate benchmark dataset (CSV/JSONL) with BERT or LLM:', fg='cyan', bold=True)}
     $ python pipeline/cli.py analyze --dataset pipeline/data/benchmarks/allsides.csv --detector bert
"""

ANALYZE_HELP_EPILOG = f"""{click.style('Examples:', fg='bright_yellow', bold=True)}
  {click.style('1. Multidimensional LLM detection on direct news text:', fg='cyan', bold=True)}
     $ python pipeline/cli.py analyze --text "The legislation passed amid controversy." --detector llm

  {click.style('2. Swap Hugging Face model checkpoint (e.g. BABE lexical bias or custom weights):', fg='cyan', bold=True)}
     $ python pipeline/cli.py analyze --detector bert --model mediabiasgroup/roberta-babe-ft --text "..."

  {click.style('3. Audit existing articles stored in Azure Blob Storage and persist analysis:', fg='cyan', bold=True)}
     $ python pipeline/cli.py analyze --storage azure --limit 10 --save

  {click.style('4. Evaluate an offline benchmark dataset (CSV or JSONL) with BERT:', fg='cyan', bold=True)}
     $ python pipeline/cli.py analyze --dataset pipeline/data/benchmarks/allsides.csv --detector bert

  {click.style('5. Analyze a specific article by ID and output structured JSON:', fg='cyan', bold=True)}
     $ python pipeline/cli.py analyze --storage azure --id 3f8a9c1b --json
"""

BENCHMARK_HELP_EPILOG = f"""{click.style('Examples:', fg='bright_yellow', bold=True)}
  {click.style('1. Benchmark default BERT model on sample dataset:', fg='cyan', bold=True)}
     $ python pipeline/cli.py benchmark --detector bert

  {click.style('2. Benchmark custom Hugging Face model (e.g. BABE lexical bias):', fg='cyan', bold=True)}
     $ python pipeline/cli.py benchmark --detector bert --model mediabiasgroup/roberta-babe-ft

  {click.style('3. Evaluate both BERT and LLM side-by-side with latency & accuracy metrics:', fg='cyan', bold=True)}
     $ python pipeline/cli.py benchmark --detector both --limit 5

  {click.style('4. Output full evaluation metrics and sample predictions to JSON:', fg='cyan', bold=True)}
     $ python pipeline/cli.py benchmark --detector bert --output-json ./benchmark_report.json
"""


# ── Main group ──────────────────────────────────────────────────────────────

@click.group(cls=ColoredGroup, epilog=MAIN_HELP_EPILOG, invoke_without_command=True)
@click.option(
    "--storage", "-st",
    type=click.Choice(["file", "azure"], case_sensitive=False),
    default=None,
    help="Override article storage backend (file or azure).",
)
@click.pass_context
def cli(ctx, storage):
    """DistillNews — AI-Powered News Aggregation Pipeline."""
    _apply_storage(storage)
    if ctx.invoked_subcommand is None:
        _launch_tui()


# ── TUI ─────────────────────────────────────────────────────────────────────

@cli.command()
@click.option(
    "--storage", "-st",
    type=click.Choice(["file", "azure"], case_sensitive=False),
    default=None,
    help="Override article storage backend (file or azure).",
)
def tui(storage):
    """Launch the interactive TUI dashboard."""
    _apply_storage(storage)
    _launch_tui()


@cli.command(cls=ColoredCommand, epilog=ANALYZE_HELP_EPILOG)
@click.option(
    "--storage", "-st",
    type=click.Choice(["file", "azure"], case_sensitive=False),
    default=None,
    help="Override article storage backend (file or azure).",
)
@click.option(
    "--detector", "-d",
    type=click.Choice(["llm", "bert"], case_sensitive=False),
    default="llm",
    help="Bias detection engine: 'llm' (default) or 'bert'.",
)
@click.option(
    "--model", "-m",
    type=str,
    default=None,
    help="HuggingFace model ID or local directory (when --detector bert).",
)
@click.option(
    "--dataset", "--file", "-f", "dataset_file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to CSV or JSONL dataset file to analyze.",
)
@click.option(
    "--id", "article_id",
    type=str,
    default=None,
    help="Analyze a specific article by ID from storage.",
)
@click.option(
    "--limit", "-n",
    type=int,
    default=5,
    help="Number of articles to analyze (default: 5).",
)
@click.option(
    "--text",
    type=str,
    default=None,
    help="Ad-hoc article text to analyze.",
)
@click.option(
    "--title",
    type=str,
    default="Custom Article",
    help="Title for ad-hoc article text.",
)
@click.option(
    "--save/--no-save",
    default=False,
    help="Save bias analysis back into article store (default: False).",
)
@click.option(
    "--json-output", "--json",
    is_flag=True,
    default=False,
    help="Output results as JSON.",
)
def analyze(storage, detector, model, dataset_file, article_id, limit, text, title, save, json_output):
    """Analyze news articles for media bias using LLM tool calling or BERT."""
    _apply_storage(storage)
    from config import config

    detector_type = detector.lower()
    bert_model = model or config.BIAS_BERT_MODEL

    agent = None
    if detector_type == "llm":
        from service.agents.factory import create_agent
        try:
            agent = create_agent()
        except Exception as e:
            click.echo(f"Error initializing LLM agent: {e}", err=True)
            sys.exit(1)

    def _run_detection(art: dict) -> dict:
        if detector_type == "bert":
            from pipeline.bias.bert_detector import analyze_article_bias_with_bert
            return analyze_article_bias_with_bert(art, model_name=bert_model)
        else:
            from pipeline.bias.llm_detector import analyze_article_bias_with_llm
            return analyze_article_bias_with_llm(art, agent)

    results = []

    # Case 1: Ad-hoc manual text
    if text:
        item = {"title": title, "content": text}
        res = _run_detection(item)
        results.append({"article": item, "title": title, "bias_analysis": res})

    # Case 2: Dataset file (CSV or JSONL)
    elif dataset_file:
        from pipeline.stages.sources.dataset import load_dataset_records
        records = list(load_dataset_records(dataset_file, limit=limit))
        if not records:
            click.echo(f"No records found in dataset file: {dataset_file}", err=True)
            return

        for idx, rec in enumerate(records, 1):
            res = _run_detection(rec)
            results.append({
                "id": f"row_{idx}",
                "title": rec.get("title", f"Row {idx}"),
                "ground_truth": rec.get("ground_truth"),
                "bias_analysis": res,
            })

    # Case 3: From storage (Azure or File)
    else:
        from service.blob.article_store import create_article_store
        try:
            store = create_article_store()
        except Exception as e:
            click.echo(f"Error initializing article store: {e}", err=True)
            sys.exit(1)

        articles_to_analyze = []
        if article_id:
            art = store.load_article(article_id)
            if not art:
                click.echo(f"Article '{article_id}' not found in storage.", err=True)
                sys.exit(1)
            articles_to_analyze.append((article_id, art))
        else:
            all_arts = store.load_all_articles(limit=limit)
            if not all_arts:
                click.echo("No articles found in storage to analyze.")
                return
            for art in all_arts:
                aid = art.get("id") or art.get("_article_id", "unknown")
                articles_to_analyze.append((aid, art))

        for aid, art in articles_to_analyze:
            res = _run_detection(art)
            art["bias_analysis"] = res
            results.append({"id": aid, "title": art.get("title", ""), "bias_analysis": res})
            if save:
                try:
                    store.save_article(art, article_id=aid)
                except Exception as e:
                    click.echo(f"Warning: Failed to save article {aid}: {e}", err=True)

    # Output formatting
    if json_output:
        import json
        click.echo(json.dumps(results, indent=2))
        return

    # Terminal pretty printer
    engine_label = f"BERT ({bert_model})" if detector_type == "bert" else "LLM AGENT"
    click.echo("\n" + "=" * 70)
    click.echo(f" MEDIA BIAS ANALYSIS REPORT (DistillNews — Engine: {engine_label})")
    click.echo("=" * 70)

    for idx, r in enumerate(results, 1):
        analysis = r.get("bias_analysis", {})
        title_str = r.get("title") or r.get("article", {}).get("title", "Untitled")
        aid_str = r.get("id", "direct-input")
        gt = r.get("ground_truth")

        click.echo(f"\n[{idx}] {title_str}")
        click.echo(f"    ID:         {aid_str}")
        if gt:
            click.echo(f"    Truth:      " + click.style(str(gt), fg="blue", bold=True))

        method = analysis.get("method", "llm")
        if method == "bert":
            pred = analysis.get("predicted_label", "UNKNOWN")
            conf = analysis.get("confidence", 0.0)
            scores = analysis.get("scores", {})
            err = analysis.get("error")

            if err:
                click.echo(f"    Error:      " + click.style(err, fg="red"))
            else:
                pred_color = "green" if pred.upper() in ("CENTER", "NON-BIASED", "NEUTRAL") else "yellow"
                click.echo(f"    Predicted:  " + click.style(f"{pred} ({conf:.1%})", fg=pred_color, bold=True))
                if scores:
                    scores_str = ", ".join(f"{k}: {v:.1%}" for k, v in scores.items())
                    click.echo(f"    Scores:     {scores_str}")
        else:
            score = analysis.get("bias_score", 0.0)
            bias_types = analysis.get("bias_types", [])
            favors = analysis.get("who_it_favors", "none / neutral")
            opposes = analysis.get("who_it_opposes", "none / neutral")
            loaded = analysis.get("loaded_language", [])
            reasoning = analysis.get("reasoning", "")

            # Score color coding
            if score <= 0.25:
                score_color = "green"
                score_desc = "LOW / NEUTRAL"
            elif score <= 0.55:
                score_color = "yellow"
                score_desc = "MODERATE"
            else:
                score_color = "red"
                score_desc = "HIGH BIAS"

            click.echo(f"    Bias Score: " + click.style(f"{score:.2f} / 1.0 ({score_desc})", fg=score_color, bold=True))
            if bias_types:
                click.echo(f"    Bias Types: " + click.style(", ".join(bias_types), fg="cyan"))
            else:
                click.echo(f"    Bias Types: " + click.style("none detected", fg="green"))
            click.echo(f"    Favors:     " + click.style(favors, fg="magenta"))
            if opposes and opposes.lower() not in ("none", "none / neutral"):
                click.echo(f"    Opposes:    " + click.style(opposes, fg="bright_black"))
            if loaded:
                click.echo(f"    Loaded:     {', '.join(loaded)}")
            if reasoning:
                click.echo(f"    Reasoning:  {reasoning}")

        if save:
            click.echo("    Persisted:  " + click.style("Saved to ArticleStore", fg="green"))

    click.echo("\n" + "=" * 70 + "\n")


# ── Benchmark command ───────────────────────────────────────────────────────

@cli.command(cls=ColoredCommand, epilog=BENCHMARK_HELP_EPILOG)
@click.option(
    "--dataset", "-d", "dataset_path",
    type=click.Path(exists=True, dir_okay=False),
    default="pipeline/data/benchmarks/sample_bias_benchmark.csv",
    show_default=True,
    help="Path to CSV or JSONL benchmark dataset file.",
)
@click.option(
    "--detector",
    type=click.Choice(["bert", "llm", "both"], case_sensitive=False),
    default="bert",
    show_default=True,
    help="Detection engine to benchmark ('bert', 'llm', or 'both').",
)
@click.option(
    "--model", "-m",
    type=str,
    default="bucketresearch/politicalBiasBERT",
    show_default=True,
    help="HuggingFace model ID or local directory (when --detector bert or both).",
)
@click.option(
    "--limit", "-n",
    type=int,
    default=None,
    help="Maximum number of samples to evaluate.",
)
@click.option(
    "--output-json", "-o",
    type=click.Path(dir_okay=False),
    default=None,
    help="Path to write full results JSON.",
)
def benchmark(dataset_path, detector, model, limit, output_json):
    """Run automated media bias benchmark evaluation on labeled datasets."""
    from pipeline.benchmark.run_bias_benchmark import evaluate_bias_benchmark, print_benchmark_report

    try:
        report = evaluate_bias_benchmark(
            dataset_path=dataset_path,
            detector=detector.lower(),
            model_name=model,
            limit=limit,
        )
        print_benchmark_report(report)

        if output_json:
            import json
            out_file = Path(output_json)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, indent=2)
            click.echo(f"Saved full benchmark report to: {out_file}")
    except Exception as e:
        click.echo(f"Benchmark error: {e}", err=True)
        sys.exit(1)


def _launch_tui():
    """Start the Textual TUI application."""
    from pipeline.tui.app import DistillNewsApp
    app = DistillNewsApp()
    app.run()


# ── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli()


