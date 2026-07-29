from typing import List, Dict, Tuple

def _normalize_cat(cat_name: str | None) -> str:
    """Normalize category string for case-insensitive matching."""
    return str(cat_name or "").strip().lower()

def sort_articles(
    preferences: List[str],
    weights: Dict[str, float],
    interactions: Dict[str, Tuple[int, float]],
    articles: List[Dict]
) -> List[Dict]:
    """
    Rank a list of articles by user preference, implicit bias weights, and engagement.

    :param preferences: Explicit list of user preference categories.
    :param weights: Mapping from category to its recommendation weight.
    :param interactions: Mapping from category to a tuple (popularity, total_duration).
    :param articles: List of articles with id, category, popularity, duration.
    :return: Articles sorted by descending recommendation score.
    """
    scored = []
    
    # Map normalized weights and interactions
    norm_weights = {_normalize_cat(k): v for k, v in weights.items()}
    norm_interactions = {_normalize_cat(k): v for k, v in interactions.items()}
    
    max_popularity = max((art.get('popularity', 0) for art in articles), default=1)
    max_duration = max((art.get('duration', 0.0) for art in articles), default=1.0)
    
    for art in articles:
        cat = _normalize_cat(art.get('category'))
        art_popularity = art.get('popularity', 0) / max_popularity if max_popularity > 0 else 0
        art_time = art.get('duration', 0.0) / max_duration if max_duration > 0 else 0
        popularity_score = 0.6 * art_popularity + 0.4 * art_time
        
        user_popularity, user_time = norm_interactions.get(cat, (0, 0.0))
        engagement_bonus = 0.2 if (user_popularity > 0 or user_time > 0) else 0.0
        
        if cat in norm_weights and norm_weights[cat] > 0:
            preference_score = norm_weights[cat]
            score = preference_score * (1.0 + popularity_score + engagement_bonus)
        else:
            # Baseline score for non-preferred categories so popular news is still discoverable
            score = 0.05 * (1.0 + popularity_score)
            
        scored.append((art, score))

from datetime import datetime, timezone

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

    scored.sort(key=lambda x: (x[1], get_publication_timestamp(x[0])), reverse=True)
    return [item[0] for item in scored]

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
    If the user views an article outside their initial preferences, that category
    is dynamically added to their recommendation weights.

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

    # Find matching key in weights or capitalize new category
    target_key = next((k for k in weights if _normalize_cat(k) == norm_cat), article_category.strip().capitalize())
    
    # Record interaction stats
    prev_popularity, prev_time = interactions.get(target_key, (0, 0.0))
    interactions[target_key] = (prev_popularity + (1 if clicked else 0), prev_time + duration)
    
    # Feedback score calculation: click bonus (1.0) + duration bonus (up to 1.0 for 60s)
    feedback = (1.0 if clicked else 0.0) + min(duration / 60.0, 1.0)
    
    current_val = weights.get(target_key, 0.0)
    weights[target_key] = current_val + (learning_rate * feedback)
    
    # Normalize all weights so they sum to 1.0
    total = sum(weights.values())
    if total > 0:
        for cat in list(weights.keys()):
            weights[cat] = weights[cat] / total
            
    return weights
