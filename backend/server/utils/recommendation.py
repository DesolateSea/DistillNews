from typing import List, Dict, Tuple

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
    
    max_popularity = max((art.get('popularity', 0) for art in articles), default=1)
    max_duration = max((art.get('duration', 0.0) for art in articles), default=1.0)
    
    for art in articles:
        cat = art.get('category')
        
        if cat in weights:
            art_popularity = art.get('popularity', 0) / max_popularity if max_popularity > 0 else 0
            art_time = art.get('duration', 0.0) / max_duration if max_duration > 0 else 0
            
            preference_score = weights[cat]
            
            popularity_score = 0.6 * art_popularity + 0.4 * art_time
            
            user_popularity, user_time = interactions.get(cat, (0, 0.0))
            engagement_bonus = 0.0
            if user_popularity > 0 or user_time > 0:
                engagement_bonus = 0.2
            
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
    prev_popularity, prev_time = interactions.get(article_category, (0, 0.0))
    interactions[article_category] = (prev_popularity + (1 if clicked else 0), prev_time + duration)
    
    if article_category in weights:
        feedback = (1.0 if clicked else 0.0) + min(duration / 60.0, 1.0)
        
        weights[article_category] += learning_rate * feedback
        
        total = sum(weights.values())
        if total > 0:
            for cat in weights:
                weights[cat] /= total
    
    return weights

# Example usage
if __name__ == "__main__":
    preferences = ["sports", "technology", "health", "business"]
    weights = {"sports": 0.25, "technology": 0.25, "health": 0.25, "business": 0.25}

    interactions = {
        "sports" : (0, 0),
        "technology" : (0, 0),
        "health" : (0, 0),
        "business" : (0, 0)
    }

    articles = [
        {"id": 1, "category": "sports", "popularity": 15, "duration": 200.0},
        {"id": 2, "category": "technology", "popularity": 5, "duration": 50.0},
        {"id": 3, "category": "health", "popularity": 2, "duration": 2000.0},
        {"id": 4, "category": "business", "popularity": 8, "duration": 100.0},
        {"id": 5, "category": "technology", "popularity": 10, "duration": 120.0}
    ]

    print("Sorted Articles:")
    sorted_articles = sort_articles(preferences, weights, interactions, articles)
    for article in sorted_articles:
        print(article)

    print("\nUpdated Weights:")
    updated_weights = update_weights(weights, interactions, "sports", True, 30.0)
    print(updated_weights)
