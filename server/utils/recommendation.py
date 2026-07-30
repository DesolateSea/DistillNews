"""
Recommendation Algorithm & Personalization Utility.
Ranks news articles based on explicit user preferences, implicit feedback weights,
engagement metrics, and publication freshness.
"""

from typing import List, Dict, Tuple
from datetime import datetime, timezone

# Standard category alias mapping for robust matching
CATEGORY_ALIASES = {
    "tech": "technology",
    "technology": "technology",
    "business": "business",
    "biz": "business",
    "finance": "business",
    "financial": "business",
    "science": "science",
    "sci": "science",
    "health": "health",
    "sports": "sports",
    "sport": "sports",
    "entertainment": "entertainment",
    "world": "world",
    "general": "general",
}


def _normalize_cat(cat_name: str | None) -> str:
    """Normalize category string for case-insensitive and alias matching."""
    raw = str(cat_name or "").strip().lower()
    return CATEGORY_ALIASES.get(raw, raw)


def get_publication_timestamp(art: dict) -> float:
    """Extract numeric epoch timestamp from publication_date / published_at for sorting."""
    if not isinstance(art, dict):
        return 0.0
    val = art.get("publication_date") or art.get("published_at") or art.get("created_at")
    if not val:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        val_str = val.strip()
        if not val_str:
            return 0.0
        try:
            return float(val_str)
        except ValueError:
            pass
        try:
            if val_str.endswith("Z"):
                val_str = val_str[:-1] + "+00:00"
            dt = datetime.fromisoformat(val_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except Exception:
            pass
    return 0.0


def sort_articles(
    preferences: List[str],
    weights: Dict[str, float],
    interactions: Dict[str, Tuple[int, float]],
    articles: List[Dict]
) -> List[Dict]:
    """
    Rank a list of articles by user preference, implicit bias weights, engagement, and freshness.

    :param preferences: Explicit list of user preference categories.
    :param weights: Mapping from category to its recommendation weight.
    :param interactions: Mapping from category to a tuple (popularity, total_duration).
    :param articles: List of articles with id, category, popularity, duration.
    :return: Articles sorted by descending recommendation score, tie-broken by publication date.
    """
    if not articles:
        return []

    norm_prefs = {_normalize_cat(p) for p in preferences if p}

    # Normalize weights map
    norm_weights: Dict[str, float] = {}
    if weights:
        for k, v in weights.items():
            norm_weights[_normalize_cat(k)] = float(v)

    # Fallback weights from explicit preferences if weights dict is empty or unpopulated
    if norm_prefs and (not norm_weights or sum(norm_weights.values()) == 0):
        equal_weight = 1.0 / len(norm_prefs)
        for p in norm_prefs:
            norm_weights[p] = equal_weight

    norm_interactions = {_normalize_cat(k): v for k, v in interactions.items()}

    max_popularity = max((art.get('popularity', 0) for art in articles if isinstance(art, dict)), default=1)
    max_duration = max((art.get('duration', 0.0) for art in articles if isinstance(art, dict)), default=1.0)
    if max_popularity <= 0:
        max_popularity = 1
    if max_duration <= 0:
        max_duration = 1.0

    scored = []

    for art in articles:
        if not isinstance(art, dict):
            continue

        cat = _normalize_cat(art.get('category'))
        art_popularity = art.get('popularity', 0) / max_popularity
        art_time = art.get('duration', 0.0) / max_duration
        popularity_score = 0.6 * art_popularity + 0.4 * art_time

        user_popularity, user_time = norm_interactions.get(cat, (0, 0.0))
        engagement_bonus = 0.2 if (user_popularity > 0 or user_time > 0) else 0.0

        # Preference weight for category
        pref_weight = norm_weights.get(cat, 0.0)

        if pref_weight > 0 or cat in norm_prefs:
            if pref_weight <= 0:
                pref_weight = 1.0 / max(len(norm_prefs), 1)
            score = pref_weight * (1.0 + popularity_score + engagement_bonus)
        else:
            # Baseline score for non-preferred categories so top breaking news remains discoverable
            score = 0.05 * (1.0 + popularity_score)

        pub_time = get_publication_timestamp(art)
        scored.append((art, score, pub_time))

    # Sort primarily by recommendation score descending, secondarily by publication timestamp descending (newest first)
    scored.sort(key=lambda x: (x[1], x[2]), reverse=True)

    return [art for art, _, _ in scored]


def update_weights(
    weights: Dict[str, float],
    interactions: Dict[str, Tuple[int, float]],
    article_category: str | None,
    clicked: bool,
    duration: float,
    learning_rate: float = 0.15
) -> Dict[str, float]:
    """
    Update category weights when a user interacts with an article.

    :param weights: Current weights per category.
    :param interactions: Current interaction history.
    :param article_category: Category of the viewed article.
    :param clicked: Whether the article was clicked.
    :param duration: Time spent viewing the article (in seconds).
    :param learning_rate: Weight adjustment rate.
    :return: Updated weights normalized to sum to 1.0.
    """
    if not article_category:
        return weights

    norm_cat = _normalize_cat(article_category)
    if not norm_cat:
        return weights

    # Copy weights dictionary to avoid mutating callers in-place unexpectedly
    new_weights = dict(weights) if weights else {}

    target_key = next((k for k in new_weights if _normalize_cat(k) == norm_cat), article_category.strip().capitalize())

    # Record interaction stats
    prev_popularity, prev_time = interactions.get(target_key, (0, 0.0))
    interactions[target_key] = (prev_popularity + (1 if clicked else 0), prev_time + duration)

    # Feedback score calculation: click bonus (1.0) + duration bonus (up to 1.0 for 60s)
    feedback = (1.0 if clicked else 0.0) + min(duration / 60.0, 1.0)

    current_val = new_weights.get(target_key, 0.0)
    new_weights[target_key] = current_val + (learning_rate * feedback)

    # Normalize all weights so they sum to 1.0
    total = sum(new_weights.values())
    if total > 0:
        for cat in list(new_weights.keys()):
            new_weights[cat] = new_weights[cat] / total

    return new_weights
