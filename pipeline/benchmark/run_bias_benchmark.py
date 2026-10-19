"""Media bias benchmark evaluation harness.

Evaluates and compares BERT sequence classification models and LLM agent detectors
against labeled media bias datasets (e.g. AllSides, BABE, MBIB).
Computes classification accuracy, class-level precision/recall/F1,
score distributions, latency statistics, and confusion matrices.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
import time
from typing import Any

import click

from pipeline.stages.sources.dataset import load_dataset_records
from pipeline.bias.bert_detector import analyze_article_bias_with_bert
from pipeline.bias.llm_detector import analyze_article_bias_with_llm

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
    samples: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_path": self.dataset_path,
            "total_samples": self.total_samples,
            "duration_seconds": round(self.duration_seconds, 2),
            "detector": self.detector,
            "bert_metrics": self.bert_metrics,
            "llm_metrics": self.llm_metrics,
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


def evaluate_bias_benchmark(
    dataset_path: str | Path,
    detector: str = "both",
    model_name: str = "bucketresearch/politicalBiasBERT",
    limit: int | None = None,
    agent: Any = None,
) -> BenchmarkReport:
    """Run benchmark evaluation against a dataset file.

    Args:
        dataset_path: CSV or JSONL file path.
        detector: 'bert', 'llm', or 'both'.
        model_name: Hugging Face checkpoint name for BERT.
        limit: Optional maximum number of records to evaluate.
        agent: Initialized AgentProvider instance for LLM (created automatically if None).

    Returns:
        Populated BenchmarkReport object.
    """
    path = Path(dataset_path)
    records = list(load_dataset_records(path, limit=limit))
    if not records:
        raise ValueError(f"No records found in dataset file: {path}")

    start_time = time.perf_counter()

    bert_y_true: list[str] = []
    bert_y_pred: list[str] = []
    bert_latencies: list[float] = []

    llm_scores: list[float] = []
    llm_types_counter: Counter[str] = Counter()
    llm_latencies: list[float] = []
    llm_scores_by_ground_truth: dict[str, list[float]] = defaultdict(list)

    samples_detail: list[dict[str, Any]] = []

    # Initialize LLM agent if needed
    if detector in ("llm", "both") and agent is None:
        from service.agents.factory import create_agent
        agent = create_agent()

    # Determine BERT model label space upfront if BERT enabled
    bert_labels: list[str] = []
    if detector in ("bert", "both"):
        from pipeline.bias.bert_detector import load_bert_model_and_tokenizer
        try:
            _, _, label_map = load_bert_model_and_tokenizer(model_name)
            bert_labels = [label_map[i] for i in sorted(label_map.keys())]
        except Exception:
            bert_labels = ["LEFT", "CENTER", "RIGHT"]

    target_labels_set = set(bert_labels)

    for idx, rec in enumerate(records, 1):
        raw_gt = rec.get("ground_truth")
        title = rec.get("title", f"Article {idx}")
        sample_log: dict[str, Any] = {
            "index": idx,
            "title": title,
            "raw_ground_truth": raw_gt,
        }

        # 1. BERT Evaluation
        if detector in ("bert", "both"):
            t0 = time.perf_counter()
            bert_res = analyze_article_bias_with_bert(rec, model_name=model_name)
            bert_latency_ms = (time.perf_counter() - t0) * 1000.0
            bert_latencies.append(bert_latency_ms)

            pred_label = bert_res.get("predicted_label", "UNKNOWN")
            norm_gt = normalize_ground_truth(raw_gt, target_labels_set) if raw_gt else None

            sample_log["bert"] = {
                "predicted": pred_label,
                "confidence": bert_res.get("confidence", 0.0),
                "normalized_truth": norm_gt,
                "latency_ms": round(bert_latency_ms, 1),
            }

            if norm_gt:
                bert_y_true.append(norm_gt)
                bert_y_pred.append(pred_label)

        # 2. LLM Evaluation
        if detector in ("llm", "both"):
            t0 = time.perf_counter()
            llm_res = analyze_article_bias_with_llm(rec, agent)
            llm_latency_ms = (time.perf_counter() - t0) * 1000.0
            llm_latencies.append(llm_latency_ms)

            b_score = llm_res.get("bias_score", 0.0)
            b_types = llm_res.get("bias_types", [])
            llm_scores.append(b_score)
            for t in b_types:
                llm_types_counter[t] += 1

            if raw_gt:
                llm_scores_by_ground_truth[str(raw_gt).upper()].append(b_score)

            sample_log["llm"] = {
                "bias_score": b_score,
                "bias_types": b_types,
                "favors": llm_res.get("who_it_favors", "none / neutral"),
                "opposes": llm_res.get("who_it_opposes", "none / neutral"),
                "latency_ms": round(llm_latency_ms, 1),
            }

        samples_detail.append(sample_log)

    duration = time.perf_counter() - start_time

    # Compute BERT metrics
    bert_metrics = None
    if detector in ("bert", "both"):
        cls_metrics = compute_classification_metrics(bert_y_true, bert_y_pred, bert_labels)
        bert_metrics = {
            "model_name": model_name,
            **cls_metrics,
            "avg_latency_ms": round(sum(bert_latencies) / len(bert_latencies), 1) if bert_latencies else 0.0,
            "p95_latency_ms": round(sorted(bert_latencies)[int(0.95 * len(bert_latencies))], 1) if bert_latencies else 0.0,
        }

    # Compute LLM metrics
    llm_metrics = None
    if detector in ("llm", "both"):
        avg_score = sum(llm_scores) / len(llm_scores) if llm_scores else 0.0
        scores_by_gt = {
            gt: round(sum(scores) / len(scores), 3)
            for gt, scores in llm_scores_by_ground_truth.items()
            if scores
        }
        llm_metrics = {
            "avg_bias_score": round(avg_score, 3),
            "bias_types_distribution": dict(llm_types_counter.most_common()),
            "avg_score_by_ground_truth": scores_by_gt,
            "avg_latency_ms": round(sum(llm_latencies) / len(llm_latencies), 1) if llm_latencies else 0.0,
            "p95_latency_ms": round(sorted(llm_latencies)[int(0.95 * len(llm_latencies))], 1) if llm_latencies else 0.0,
        }

    return BenchmarkReport(
        dataset_path=str(path),
        total_samples=len(records),
        duration_seconds=duration,
        detector=detector,
        bert_metrics=bert_metrics,
        llm_metrics=llm_metrics,
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

    # BERT Metrics
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

    # LLM Metrics
    if report.llm_metrics:
        lm = report.llm_metrics
        click.echo("\n" + "-" * 72)
        click.echo(click.style(" LLM Agent Detection Analytics", fg="cyan", bold=True))
        click.echo("-" * 72)

        click.echo(f"  Average Bias Score: {lm.get('avg_bias_score'):.3f} / 1.0")
        click.echo(f"  Average Latency:    {lm.get('avg_latency_ms')} ms/article (p95: {lm.get('p95_latency_ms')} ms)")

        by_gt = lm.get("avg_score_by_ground_truth", {})
        if by_gt:
            click.echo("\n  Average LLM Bias Score by Ground-Truth Category:")
            for gt_cat, avg_s in sorted(by_gt.items()):
                score_color = "green" if avg_s <= 0.25 else "yellow" if avg_s <= 0.55 else "red"
                click.echo(f"    {gt_cat:<16}: " + click.style(f"{avg_s:.3f}", fg=score_color, bold=True))

        dist = lm.get("bias_types_distribution", {})
        if dist:
            click.echo("\n  Detected Bias Types Frequency:")
            for btype, cnt in dist.items():
                click.echo(f"    {btype:<20}: {cnt} occurrences")

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
