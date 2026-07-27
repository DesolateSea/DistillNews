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
    Rank a list of articles by user preference and engagement.

    :param preferences: Ordered list of user preference categories.
    :param weights: Mapping from preference category to its weight.
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
        
        if cat in norm_weights and norm_weights[cat] > 0:
            art_popularity = art.get('popularity', 0) / max_popularity if max_popularity > 0 else 0
            art_time = art.get('duration', 0.0) / max_duration if max_duration > 0 else 0
            
            preference_score = norm_weights[cat]
            popularity_score = 0.6 * art_popularity + 0.4 * art_time
            
            user_popularity, user_time = norm_interactions.get(cat, (0, 0.0))
            engagement_bonus = 0.2 if (user_popularity > 0 or user_time > 0) else 0.0
            
            score = preference_score * (1.0 + popularity_score + engagement_bonus)
        else:
            score = 0.0
            
        scored.append((art, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [item[0] for item in scored]

def update_weights(
    weights: Dict[str, float],
    interactions: Dict[str, Tuple[int, float]],
    article_category: str,
    clicked: bool,
    duration: float,
    learning_rate: float = 0.1
) -> Dict[str, float]:
    """
    Update the weights when a user interacts with an article.

    :param weights: Current weights per category.
    :param interactions: Current interaction history.
    :param article_category: Category of the article.
    :param clicked: Whether the article was clicked.
    :param duration: Time spent viewing the article.
    :param learning_rate: Weight adjustment rate.
    :return: Updated weights normalized to sum to 1.
    """
    norm_cat = _normalize_cat(article_category)
    
    # Find matching key in weights (preserve original key casing in weights dict)
    target_key = next((k for k in weights if _normalize_cat(k) == norm_cat), article_category)
    
    prev_popularity, prev_time = interactions.get(target_key, (0, 0.0))
    interactions[target_key] = (prev_popularity + (1 if clicked else 0), prev_time + duration)
    
    if target_key in weights:
        feedback = (1.0 if clicked else 0.0) + min(duration / 60.0, 1.0)
        weights[target_key] += learning_rate * feedback
        
        total = sum(weights.values())
        if total > 0:
            for cat in weights:
                weights[cat] /= total
    
    return weights
