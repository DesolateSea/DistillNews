"""Media bias benchmark evaluation harness.

Evaluates and compares BERT sequence classification models and LLM agent detectors
against labeled media bias datasets (e.g. AllSides, BABE, MBIB).
Computes classification accuracy, class-level precision/recall/F1,
latency statistics, confusion matrices, and head-to-head model comparisons.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
import tempfile
import time
from typing import Any

import click

from pipeline.stages.sources.dataset import load_dataset_records
from pipeline.bias.bert_detector import analyze_article_bias_with_bert
from pipeline.bias.llm_detector import classify_article_bias_with_llm

logger = logging.getLogger(__name__)


# Standard mappings to align varied benchmark ground-truth strings to model label conventions
LABEL_SYNONYMS: dict[str, str] = {
    # Ideological stance
    "left": "LEFT",
    "lean left": "LEFT",
    "far left": "LEFT",
    "liberal": "LEFT",
    "democrat": "LEFT",
    "center": "CENTER",
    "neutral": "CENTER",
    "balanced": "CENTER",
    "non-partisan": "CENTER",
    "right": "RIGHT",
    "lean right": "RIGHT",
    "far right": "RIGHT",
    "conservative": "RIGHT",
    "republican": "RIGHT",
    # Binary lexical bias (BABE)
    "biased": "BIASED",
    "bias": "BIASED",
    "1": "BIASED",
    "non-biased": "NON-BIASED",
    "unbiased": "NON-BIASED",
    "0": "NON-BIASED",
}


def normalize_ground_truth(raw: str | None, target_labels: set[str]) -> str | None:
    """Normalize raw dataset label to match target model's label space."""
    if not raw:
        return None

    clean = str(raw).strip().lower()
    canonical = LABEL_SYNONYMS.get(clean, str(raw).strip())

    # Check direct match (case-insensitive) against model classes
    for lbl in target_labels:
        if canonical.upper() == lbl.upper():
            return lbl

    # Fallback substring check
    for lbl in target_labels:
        if lbl.upper() in canonical.upper():
            return lbl

    return canonical


@dataclass
class BenchmarkReport:
    """Aggregated evaluation metrics for a benchmark run."""

    dataset_path: str
    total_samples: int
    duration_seconds: float
    detector: str
    bert_metrics: dict[str, Any] | None = None
    llm_metrics: dict[str, Any] | None = None
    comparison_metrics: dict[str, Any] | None = None
    samples: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_path": self.dataset_path,
            "total_samples": self.total_samples,
            "duration_seconds": round(self.duration_seconds, 2),
            "detector": self.detector,
            "bert_metrics": self.bert_metrics,
            "llm_metrics": self.llm_metrics,
            "comparison_metrics": self.comparison_metrics,
            "samples": self.samples,
        }


def compute_classification_metrics(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict[str, Any]:
    """Calculate multi-class or binary accuracy, precision, recall, and F1."""
    if not y_true or not y_pred:
        return {"accuracy": 0.0, "total_evaluated": 0}

    total = len(y_true)
    correct = sum(1 for yt, yp in zip(y_true, y_pred) if yt.upper() == yp.upper())
    accuracy = correct / total if total > 0 else 0.0

    # Confusion matrix
    matrix: dict[str, dict[str, int]] = {l: {l2: 0 for l2 in labels} for l in labels}
    for yt, yp in zip(y_true, y_pred):
        if yt in matrix and yp in matrix[yt]:
            matrix[yt][yp] += 1

    # Per-class metrics
    per_class: dict[str, dict[str, float]] = {}
    f1_list = []
    for l in labels:
        tp = matrix.get(l, {}).get(l, 0)
        fp = sum(matrix.get(other, {}).get(l, 0) for other in labels if other != l)
        fn = sum(matrix.get(l, {}).get(other, 0) for other in labels if other != l)

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        f1_list.append(f1)

        per_class[l] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": tp + fn,
        }

    macro_f1 = sum(f1_list) / len(f1_list) if f1_list else 0.0

    return {
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "total_evaluated": total,
        "correct": correct,
        "per_class": per_class,
        "confusion_matrix": matrix,
    }


def resolve_benchmark_dataset(dataset_spec: str | Path) -> Path:
    """Resolve dataset alias ('babe', 'allsides', 'sample') or file path."""
    spec_str = str(dataset_spec).strip()
    spec_lower = spec_str.lower()
    temp_dir = Path(tempfile.gettempdir())

    if spec_lower in ("babe", "mediabiasgroup/babe"):
        candidates = [
            Path("pipeline/data/benchmarks/babe_benchmark.csv"),
            temp_dir / "babe_benchmark.csv",
        ]
        for c in candidates:
            if c.is_file():
                return c
        return _fetch_and_prepare_babe()

    if spec_lower in ("allsides", "all-sides", "liyucheng/allsides"):
        candidates = [
            Path("pipeline/data/benchmarks/allsides_benchmark.csv"),
            temp_dir / "allsides_benchmark.csv",
        ]
        for c in candidates:
            if c.is_file():
                return c
        return _fetch_and_prepare_allsides()

    if spec_lower in ("sample", "default"):
        return Path("pipeline/data/benchmarks/sample_bias_benchmark.csv")

    path = Path(dataset_spec)
    if not path.is_file():
        repo_candidate = Path("pipeline/data/benchmarks") / spec_str
        if repo_candidate.is_file():
            return repo_candidate
        tmp_candidate = temp_dir / spec_str
        if tmp_candidate.is_file():
            return tmp_candidate
    return path


def _fetch_and_prepare_babe() -> Path:
    """Download and format BABE benchmark (1,000 sentences) from Hugging Face."""
    out_path = Path(tempfile.gettempdir()) / "babe_benchmark.csv"
    if out_path.is_file():
        return out_path
    try:
        from huggingface_hub import hf_hub_download
        import pandas as pd
        p = hf_hub_download(repo_id="mediabiasgroup/BABE", filename="data/test-00000-of-00001.parquet", repo_type="dataset")
        df = pd.read_parquet(p)
        clean_df = pd.DataFrame({
            "title": df["topic"].fillna("News").astype(str),
            "text": df["text"],
            "label": df["label"].map({0: "Non-biased", 1: "Biased"}),
        })
        clean_df.to_csv(out_path, index=False)
        return out_path
    except Exception as e:
        logger.error("Failed to fetch BABE dataset from Hugging Face: %s", e)
        raise


def _fetch_and_prepare_allsides() -> Path:
    """Download and format AllSides benchmark (714 balanced articles) from Hugging Face."""
    out_path = Path(tempfile.gettempdir()) / "allsides_benchmark.csv"
    if out_path.is_file():
        return out_path
    try:
        from huggingface_hub import hf_hub_download
        import pandas as pd
        p = hf_hub_download(repo_id="liyucheng/allsides", filename="data/train-00000-of-00001-da1e7ddeb6190432.parquet", repo_type="dataset")
        df = pd.read_parquet(p)
        valid = df[df["articles"].str.len() > 50].copy()
        valid["clean_label"] = valid["camp"].map({"lefts": "Left", "centers": "Center", "rights": "Right"})
        valid = valid.dropna(subset=["clean_label"])
        clean_df = pd.DataFrame({
            "title": valid["title"],
            "text": valid["articles"],
            "label": valid["clean_label"],
        })
        clean_df.to_csv(out_path, index=False)
        return out_path
    except Exception as e:
        logger.error("Failed to fetch AllSides dataset from Hugging Face: %s", e)
        raise


def evaluate_bias_benchmark(
    dataset_path: str | Path,
    detector: str = "both",
    model_name: str = "bucketresearch/politicalBiasBERT",
    limit: int | None = None,
    agent: Any = None,
) -> BenchmarkReport:
    """Run benchmark evaluation against a dataset file or alias ('babe', 'allsides', 'sample').

    Args:
        dataset_path: CSV or JSONL file path, or alias name.
        detector: 'bert', 'llm', or 'both'.
        model_name: Hugging Face checkpoint name for BERT.
        limit: Optional maximum number of records to evaluate.
        agent: Initialized AgentProvider instance for LLM (created automatically if None).

    Returns:
        Populated BenchmarkReport object.
    """
    path = resolve_benchmark_dataset(dataset_path)
    records = list(load_dataset_records(path, limit=limit))
    if not records:
        raise ValueError(f"No records found in dataset file: {path}")

    start_time = time.perf_counter()

    bert_y_true: list[str] = []
    bert_y_pred: list[str] = []
    bert_latencies: list[float] = []

    llm_y_true: list[str] = []
    llm_y_pred: list[str] = []
    llm_latencies: list[float] = []

    all_bert_preds: list[str] = []
    all_llm_preds: list[str] = []

    samples_detail: list[dict[str, Any]] = []

    # Initialize LLM agent if needed
    if detector in ("llm", "both") and agent is None:
        from service.agents.factory import create_agent
        agent = create_agent()

    # Determine BERT model label space upfront if BERT enabled
    target_labels: list[str] = []
    if detector in ("bert", "both"):
        from pipeline.bias.bert_detector import load_bert_model_and_tokenizer
        try:
            _, _, label_map = load_bert_model_and_tokenizer(model_name)
            target_labels = [label_map[i] for i in sorted(label_map.keys())]
        except Exception:
            target_labels = ["LEFT", "CENTER", "RIGHT"]
    else:
        # If running only LLM, inspect dataset records to infer label space or default to 3-class
        sample_gts = {rec.get("ground_truth") for rec in records if rec.get("ground_truth")}
        is_binary = any(str(g).upper() in ("BIASED", "NON-BIASED", "1", "0") for g in sample_gts)
        target_labels = ["NON-BIASED", "BIASED"] if is_binary else ["LEFT", "CENTER", "RIGHT"]

    target_labels_set = set(target_labels)

    for idx, rec in enumerate(records, 1):
        raw_gt = rec.get("ground_truth")
        title = rec.get("title", f"Article {idx}")
        norm_gt = normalize_ground_truth(raw_gt, target_labels_set) if raw_gt else None

        sample_log: dict[str, Any] = {
            "index": idx,
            "title": title,
            "raw_ground_truth": raw_gt,
            "normalized_truth": norm_gt,
        }

        # 1. BERT Evaluation
        pred_bert = None
        if detector in ("bert", "both"):
            t0 = time.perf_counter()
            bert_res = analyze_article_bias_with_bert(rec, model_name=model_name)
            bert_latency_ms = (time.perf_counter() - t0) * 1000.0
            bert_latencies.append(bert_latency_ms)

            pred_bert = bert_res.get("predicted_label", "UNKNOWN")
            all_bert_preds.append(pred_bert)

            sample_log["bert"] = {
                "predicted": pred_bert,
                "confidence": bert_res.get("confidence", 0.0),
                "scores": bert_res.get("scores", {}),
                "latency_ms": round(bert_latency_ms, 1),
            }

            if norm_gt:
                bert_y_true.append(norm_gt)
                bert_y_pred.append(pred_bert)

        # 2. LLM Categorical Evaluation
        pred_llm = None
        if detector in ("llm", "both"):
            t0 = time.perf_counter()
            llm_res = classify_article_bias_with_llm(rec, agent, candidate_labels=target_labels)
            llm_latency_ms = (time.perf_counter() - t0) * 1000.0
            llm_latencies.append(llm_latency_ms)

            pred_llm = llm_res.get("predicted_label", "UNKNOWN")
            all_llm_preds.append(pred_llm)

            sample_log["llm"] = {
                "predicted": pred_llm,
                "confidence": llm_res.get("confidence", 0.0),
                "scores": llm_res.get("scores", {}),
                "reasoning": llm_res.get("reasoning", ""),
                "latency_ms": round(llm_latency_ms, 1),
            }

            if norm_gt:
                llm_y_true.append(norm_gt)
                llm_y_pred.append(pred_llm)

        samples_detail.append(sample_log)

    duration = time.perf_counter() - start_time

    # Compute BERT metrics
    bert_metrics = None
    if detector in ("bert", "both"):
        cls_metrics = compute_classification_metrics(bert_y_true, bert_y_pred, target_labels)
        bert_metrics = {
            "model_name": model_name,
            **cls_metrics,
            "avg_latency_ms": round(sum(bert_latencies) / len(bert_latencies), 1) if bert_latencies else 0.0,
            "p95_latency_ms": round(sorted(bert_latencies)[int(0.95 * len(bert_latencies))], 1) if bert_latencies else 0.0,
        }

    # Compute LLM metrics
    llm_metrics = None
    if detector in ("llm", "both"):
        cls_metrics = compute_classification_metrics(llm_y_true, llm_y_pred, target_labels)
        llm_metrics = {
            "agent_provider": getattr(agent, "provider_name", "llm"),
            **cls_metrics,
            "avg_latency_ms": round(sum(llm_latencies) / len(llm_latencies), 1) if llm_latencies else 0.0,
            "p95_latency_ms": round(sorted(llm_latencies)[int(0.95 * len(llm_latencies))], 1) if llm_latencies else 0.0,
        }

    # Compute Head-to-Head Comparison if both were executed
    comparison_metrics = None
    if detector == "both" and all_bert_preds and all_llm_preds:
        agreement_count = sum(
            1 for b, l in zip(all_bert_preds, all_llm_preds) if b.upper() == l.upper()
        )
        total_p = len(all_bert_preds)
        agreement_rate = agreement_count / total_p if total_p > 0 else 0.0
        comparison_metrics = {
            "agreement_rate": round(agreement_rate, 4),
            "agreement_count": agreement_count,
            "total_pairs": total_p,
            "accuracy_difference": round(
                (llm_metrics.get("accuracy", 0.0) - bert_metrics.get("accuracy", 0.0)), 4
            ) if (llm_metrics and bert_metrics) else 0.0,
        }

    return BenchmarkReport(
        dataset_path=str(path),
        total_samples=len(records),
        duration_seconds=duration,
        detector=detector,
        bert_metrics=bert_metrics,
        llm_metrics=llm_metrics,
        comparison_metrics=comparison_metrics,
        samples=samples_detail,
    )


def print_benchmark_report(report: BenchmarkReport) -> None:
    """Print beautifully styled terminal summary of benchmark evaluation."""
    click.echo("\n" + "=" * 72)
    click.echo(click.style(" DISTILLNEWS MEDIA BIAS BENCHMARK REPORT", fg="bright_yellow", bold=True))
    click.echo("=" * 72)

    click.echo(f"  Dataset:      {report.dataset_path}")
    click.echo(f"  Samples:      {report.total_samples}")
    click.echo(f"  Duration:     {report.duration_seconds:.2f}s (throughput: {report.total_samples / max(0.001, report.duration_seconds):.1f} arts/s)")
    click.echo(f"  Engine Mode:  {report.detector.upper()}")

    # 1. BERT Metrics
    if report.bert_metrics:
        bm = report.bert_metrics
        click.echo("\n" + "-" * 72)
        click.echo(click.style(f" BERT Classification Performance ({bm.get('model_name')})", fg="cyan", bold=True))
        click.echo("-" * 72)

        acc = bm.get("accuracy", 0.0)
        macro_f1 = bm.get("macro_f1", 0.0)
        eval_count = bm.get("total_evaluated", 0)
        correct = bm.get("correct", 0)

        click.echo(f"  Overall Accuracy: " + click.style(f"{acc:.1%}", fg="green" if acc >= 0.70 else "yellow", bold=True) + f" ({correct}/{eval_count} samples)")
        click.echo(f"  Macro F1-Score:   " + click.style(f"{macro_f1:.3f}", fg="green" if macro_f1 >= 0.70 else "yellow", bold=True))
        click.echo(f"  Average Latency:  {bm.get('avg_latency_ms')} ms/article (p95: {bm.get('p95_latency_ms')} ms)")

        per_class = bm.get("per_class", {})
        if per_class:
            click.echo("\n  Per-Class Metrics:")
            click.echo("    Class          Precision    Recall       F1-Score     Support")
            click.echo("    " + "-" * 56)
            for cls_name, vals in per_class.items():
                p = vals.get("precision", 0.0)
                r = vals.get("recall", 0.0)
                f1 = vals.get("f1", 0.0)
                sup = vals.get("support", 0)
                click.echo(f"    {cls_name:<14} {p:>9.1%}   {r:>9.1%}   {f1:>10.3f}   {sup:>7}")

        matrix = bm.get("confusion_matrix")
        if matrix:
            classes = list(matrix.keys())
            click.echo("\n  Confusion Matrix (Rows: Ground Truth, Cols: Predicted):")
            header = "    " + " " * 14 + "".join(f"{c:>10}" for c in classes)
            click.echo(header)
            for row_label in classes:
                row_str = f"    {row_label:<14}" + "".join(f"{matrix[row_label].get(col, 0):>10}" for col in classes)
                click.echo(row_str)

    # 2. LLM Metrics
    if report.llm_metrics:
        lm = report.llm_metrics
        click.echo("\n" + "-" * 72)
        click.echo(click.style(f" LLM Agent Classification Performance ({lm.get('agent_provider')})", fg="cyan", bold=True))
        click.echo("-" * 72)

        acc = lm.get("accuracy", 0.0)
        macro_f1 = lm.get("macro_f1", 0.0)
        eval_count = lm.get("total_evaluated", 0)
        correct = lm.get("correct", 0)

        click.echo(f"  Overall Accuracy: " + click.style(f"{acc:.1%}", fg="green" if acc >= 0.70 else "yellow", bold=True) + f" ({correct}/{eval_count} samples)")
        click.echo(f"  Macro F1-Score:   " + click.style(f"{macro_f1:.3f}", fg="green" if macro_f1 >= 0.70 else "yellow", bold=True))
        click.echo(f"  Average Latency:  {lm.get('avg_latency_ms')} ms/article (p95: {lm.get('p95_latency_ms')} ms)")

        per_class = lm.get("per_class", {})
        if per_class:
            click.echo("\n  Per-Class Metrics:")
            click.echo("    Class          Precision    Recall       F1-Score     Support")
            click.echo("    " + "-" * 56)
            for cls_name, vals in per_class.items():
                p = vals.get("precision", 0.0)
                r = vals.get("recall", 0.0)
                f1 = vals.get("f1", 0.0)
                sup = vals.get("support", 0)
                click.echo(f"    {cls_name:<14} {p:>9.1%}   {r:>9.1%}   {f1:>10.3f}   {sup:>7}")

        matrix = lm.get("confusion_matrix")
        if matrix:
            classes = list(matrix.keys())
            click.echo("\n  Confusion Matrix (Rows: Ground Truth, Cols: Predicted):")
            header = "    " + " " * 14 + "".join(f"{c:>10}" for c in classes)
            click.echo(header)
            for row_label in classes:
                row_str = f"    {row_label:<14}" + "".join(f"{matrix[row_label].get(col, 0):>10}" for col in classes)
                click.echo(row_str)

    # 3. Head-to-Head Comparison (if both evaluated)
    if report.comparison_metrics and report.bert_metrics and report.llm_metrics:
        cm = report.comparison_metrics
        bm = report.bert_metrics
        lm = report.llm_metrics

        click.echo("\n" + "=" * 72)
        click.echo(click.style(" HEAD-TO-HEAD BENCHMARK COMPARISON (BERT vs LLM)", fg="bright_magenta", bold=True))
        click.echo("=" * 72)
        click.echo(f"  {'Metric':<25} {'BERT':<22} {'LLM Agent':<22}")
        click.echo("  " + "-" * 68)

        b_acc = f"{bm.get('accuracy', 0.0):.1%} ({bm.get('correct', 0)}/{bm.get('total_evaluated', 0)})"
        l_acc = f"{lm.get('accuracy', 0.0):.1%} ({lm.get('correct', 0)}/{lm.get('total_evaluated', 0)})"
        click.echo(f"  {'Overall Accuracy':<25} {b_acc:<22} {l_acc:<22}")

        b_f1 = f"{bm.get('macro_f1', 0.0):.3f}"
        l_f1 = f"{lm.get('macro_f1', 0.0):.3f}"
        click.echo(f"  {'Macro F1-Score':<25} {b_f1:<22} {l_f1:<22}")

        b_lat = f"{bm.get('avg_latency_ms', 0.0):.1f} ms"
        l_lat = f"{lm.get('avg_latency_ms', 0.0):.1f} ms"
        click.echo(f"  {'Average Latency':<25} {b_lat:<22} {l_lat:<22}")

        agr = cm.get('agreement_rate', 0.0)
        click.echo(f"\n  Inter-Model Agreement: " + click.style(f"{agr:.1%}", fg="cyan", bold=True) + f" ({cm.get('agreement_count')}/{cm.get('total_pairs')} samples predicted identically)")

    click.echo("\n" + "=" * 72 + "\n")


def main() -> None:
    """CLI entry point for running bias benchmark evaluations."""
    parser = argparse.ArgumentParser(description="Evaluate media bias models and LLM detectors on benchmark datasets.")
    parser.add_argument("--dataset", "-d", required=True, help="Path to CSV or JSONL benchmark dataset.")
    parser.add_argument("--detector", choices=["bert", "llm", "both"], default="both", help="Detection engine to evaluate.")
    parser.add_argument("--model", "-m", default="bucketresearch/politicalBiasBERT", help="BERT checkpoint repo ID or local path.")
    parser.add_argument("--limit", "-n", type=int, default=None, help="Maximum number of samples to evaluate.")
    parser.add_argument("--output-json", "-o", default=None, help="Path to write full results JSON.")

    args = parser.parse_args()

    report = evaluate_bias_benchmark(
        dataset_path=args.dataset,
        detector=args.detector,
        model_name=args.model,
        limit=args.limit,
    )

    print_benchmark_report(report)

    if args.output_json:
        out_path = Path(args.output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2)
        click.echo(f"Saved full benchmark report to: {out_path}")


if __name__ == "__main__":
    main()
