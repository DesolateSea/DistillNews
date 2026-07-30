"""Unit tests for db handles, FileStore repository, and recommendation logic using pytest."""

import pytest
from service.db import FileStore, MongoHandle, RedisHandle
from server.utils.recommendation import sort_articles, update_weights


def test_mongo_handle_lifecycle():
    assert MongoHandle._client is None
    MongoHandle.connect(url="mongodb://localhost:27017/test_db", db_name="test_db")
    assert MongoHandle._client is not None
    assert MongoHandle.get_db().name == "test_db"
    assert MongoHandle.collection("test_col").name == "test_col"
    MongoHandle.disconnect()
    assert MongoHandle._client is None

    with pytest.raises(RuntimeError, match="MongoHandle.connect\\(\\) has not been called"):
        MongoHandle.get_db()


def test_file_store_repository():
    title = "Test Headline"
    pub_date = "2026-07-24"
    article_id = FileStore.compute_article_id(title, pub_date)
    assert len(article_id) == 64

    # Test JSON save and load via FileStore repository
    test_data = {"title": title, "publication_date": pub_date, "content": "Test content"}
    saved_path = FileStore.save_processed_article(test_data, article_id=article_id)
    assert saved_path.exists()
    assert FileStore.article_exists(article_id)

    loaded = FileStore.load_processed_article(article_id)
    assert loaded["title"] == title
    assert loaded["content"] == "Test content"

    # Clean up test file
    saved_path.unlink(missing_ok=True)


def test_sort_articles_recommendation():
    preferences = ["sports", "technology"]
    weights = {"sports": 0.7, "technology": 0.3}
    interactions = {"sports": (1, 10.0), "technology": (0, 0.0)}

    articles = [
        {"id": "1", "category": "technology", "popularity": 10, "duration": 5.0},
        {"id": "2", "category": "sports", "popularity": 5, "duration": 20.0},
        {"id": "3", "category": "entertainment", "popularity": 100, "duration": 100.0},
    ]

    sorted_arts = sort_articles(preferences, weights, interactions, articles)
    assert len(sorted_arts) == 3
    assert sorted_arts[0]["id"] == "2"


def test_update_weights():
    weights = {"sports": 0.5, "technology": 0.5}
    interactions = {}

    updated = update_weights(
        weights,
        interactions,
        article_category="sports",
        clicked=True,
        duration=30.0,
        learning_rate=0.1,
    )

    assert interactions["sports"] == (1, 30.0)
    assert updated["sports"] > updated["technology"]
    assert pytest.approx(sum(updated.values()), abs=1e-5) == 1.0


def test_recommendation_empty_weights_and_tiebreaking():
    # User with explicit preferences but empty weights map
    preferences = ["Technology"]
    weights = {}
    interactions = {}

    articles = [
        {"id": "1", "category": "General", "publication_date": "2026-07-20T10:00:00Z"},
        {"id": "2", "category": "Tech", "publication_date": "2026-07-25T10:00:00Z"},
        {"id": "3", "category": "Technology", "publication_date": "2026-07-28T10:00:00Z"},
    ]

    sorted_arts = sort_articles(preferences, weights, interactions, articles)
    assert sorted_arts[0]["id"] == "3"  # Newest Technology article first
    assert sorted_arts[1]["id"] == "2"  # Tech alias matches Technology
    assert sorted_arts[2]["id"] == "1"  # General non-preferred article last
