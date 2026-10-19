"""BERT-based media bias detector using Hugging Face sequence classification models.

Dynamically inspects model.config.id2label to support arbitrary classification
heads (3-class political stance, binary lexical bias, or custom fine-tunes).
Performs sliding-window chunking with soft-voting probability aggregation
for articles exceeding the 512-token transformer limit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any

import torch
from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer

logger = logging.getLogger(__name__)

# Fallbacks for specific checkpoints where id2label contains generic 'LABEL_0', 'LABEL_1'
KNOWN_LABEL_FALLBACKS: dict[str, dict[int, str]] = {
    "mediabiasgroup/roberta-babe-ft": {0: "NON-BIASED", 1: "BIASED"},
}

_MODEL_CACHE: dict[tuple[str, str], tuple[Any, Any, dict[int, str]]] = {}


@dataclass
class BertBiasResult:
    """Standardized output container for BERT sequence classification bias evaluation."""

    method: str = "bert"
    model_name: str = ""
    predicted_label: str = "UNKNOWN"
    confidence: float = 0.0
    scores: dict[str, float] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "method": self.method,
            "model_name": self.model_name,
            "predicted_label": self.predicted_label,
            "confidence": round(self.confidence, 4),
            "scores": {k: round(v, 4) for k, v in self.scores.items()},
        }
        if self.error:
            result["error"] = self.error
        return result


def _resolve_device(device: str | None = None) -> torch.device:
    """Determine optimal compute device for transformer inference."""
    if device:
        return torch.device(device)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _extract_label_mapping(config: Any, model_name: str) -> dict[int, str]:
    """Dynamically derive index-to-label mapping from Hugging Face PretrainedConfig."""
    raw_id2label = getattr(config, "id2label", None)

    # Check if id2label is defined and non-empty
    if raw_id2label and isinstance(raw_id2label, dict):
        mapping = {}
        for k, v in raw_id2label.items():
            try:
                mapping[int(k)] = str(v)
            except (ValueError, TypeError):
                continue

        # Check if labels are all generic ('LABEL_0', 'LABEL_1', etc.)
        is_generic = all(v.upper().startswith("LABEL_") for v in mapping.values())
        if is_generic and model_name in KNOWN_LABEL_FALLBACKS:
            return KNOWN_LABEL_FALLBACKS[model_name]

        if mapping:
            return mapping

    # Fallback if config has num_labels
    num_labels = getattr(config, "num_labels", 2)
    if model_name in KNOWN_LABEL_FALLBACKS:
        return KNOWN_LABEL_FALLBACKS[model_name]

    return {i: f"LABEL_{i}" for i in range(num_labels)}


def load_bert_model_and_tokenizer(
    model_name: str,
    device: str | None = None,
) -> tuple[Any, Any, dict[int, str]]:
    """Load or retrieve cached transformer model, tokenizer, and label mapping.

    Args:
        model_name: Hugging Face repo ID (e.g. 'bucketresearch/politicalBiasBERT')
                    or path to local directory.
        device: Target torch device ('cpu', 'cuda', etc.).

    Returns:
        Tuple of (model, tokenizer, label_mapping).
    """
    target_device = _resolve_device(device)
    cache_key = (model_name, str(target_device))

    if cache_key in _MODEL_CACHE:
        return _MODEL_CACHE[cache_key]

    logger.info("Loading BERT bias model '%s' on %s...", model_name, target_device)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model.to(target_device)
    model.eval()

    label_mapping = _extract_label_mapping(model.config, model_name)
    _MODEL_CACHE[cache_key] = (model, tokenizer, label_mapping)
    return model, tokenizer, label_mapping


def analyze_article_bias_with_bert(
    article: dict[str, Any] | str,
    model_name: str = "bucketresearch/politicalBiasBERT",
    device: str | None = None,
    max_length: int = 512,
    stride: int = 64,
    max_chunks: int = 16,
) -> dict[str, Any]:
    """Evaluate article bias using a BERT sequence classification model.

    Supports chunking with soft-voting aggregation across sliding windows
    for long news articles.

    Args:
        article: Article dictionary with title and content, or plain text string.
        model_name: Hugging Face checkpoint name or local directory.
        device: Optional device override ('cpu', 'cuda').
        max_length: Maximum tokens per chunk (default: 512).
        stride: Overlap between consecutive sliding window chunks.
        max_chunks: Cap on number of chunks processed to bound execution time.

    Returns:
        Dictionary with method='bert', model_name, predicted_label, confidence,
        and all class probability scores.
    """
    # Extract text from input
    if isinstance(article, str):
        text = article.strip()
    elif isinstance(article, dict):
        title = article.get("title", "").strip()
        content = (
            article.get("content")
            or article.get("markdown_content")
            or article.get("summary")
            or ""
        ).strip()
        text = f"{title}\n\n{content}".strip() if title else content
    else:
        text = ""

    if not text:
        return BertBiasResult(
            model_name=model_name,
            predicted_label="NEUTRAL",
            confidence=0.0,
            scores={},
        ).to_dict()

    try:
        model, tokenizer, label_map = load_bert_model_and_tokenizer(model_name, device=device)
        try:
            target_device = next(iter(model.parameters())).device
        except Exception:
            target_device = _resolve_device(device)
    except Exception as e:
        logger.error("Failed to load BERT bias model '%s': %s", model_name, e)
        return BertBiasResult(
            model_name=model_name,
            predicted_label="UNKNOWN",
            confidence=0.0,
            scores={},
            error=str(e),
        ).to_dict()

    try:
        # Sliding-window tokenization
        encoded = tokenizer(
            text,
            max_length=max_length,
            truncation=True,
            stride=stride,
            return_overflowing_tokens=True,
            padding=True,
            return_tensors="pt",
        )

        input_ids = encoded["input_ids"]
        attention_mask = encoded.get("attention_mask")

        # Bound maximum chunks to prevent pathological processing times
        if input_ids.shape[0] > max_chunks:
            input_ids = input_ids[:max_chunks]
            if attention_mask is not None:
                attention_mask = attention_mask[:max_chunks]

        input_ids = input_ids.to(target_device)
        model_kwargs = {"input_ids": input_ids}
        if attention_mask is not None:
            model_kwargs["attention_mask"] = attention_mask.to(target_device)

        with torch.no_grad():
            outputs = model(**model_kwargs)
            logits = outputs.logits  # Shape: [num_chunks, num_labels]
            probs = torch.softmax(logits, dim=-1)  # Softmax per chunk
            avg_probs = probs.mean(dim=0)  # Average across all sliding chunks

        pred_idx = int(avg_probs.argmax().item())
        predicted_label = label_map.get(pred_idx, f"LABEL_{pred_idx}")
        confidence = float(avg_probs[pred_idx].item())

        scores = {
            label_map.get(i, f"LABEL_{i}"): float(avg_probs[i].item())
            for i in range(len(avg_probs))
        }

        return BertBiasResult(
            model_name=model_name,
            predicted_label=predicted_label,
            confidence=confidence,
            scores=scores,
        ).to_dict()

    except Exception as e:
        logger.error("Error during BERT inference with model '%s': %s", model_name, e)
        return BertBiasResult(
            model_name=model_name,
            predicted_label="UNKNOWN",
            confidence=0.0,
            scores={},
            error=str(e),
        ).to_dict()
