"""Unit tests for pipeline source configuration loader using pytest."""

from pipeline.sources.config import (
    GNEWS_QUERIES,
    MEDIA_STACK_CATEGORIES,
    RAPID_NEWS_SECTIONS,
    SUBREDDITS,
    NEWS_ORG_TOPICS,
    CORE_KEYWORDS,
)


def test_source_config_keywords_loaded():
    assert len(GNEWS_QUERIES) > 0
    assert "indian economy" in GNEWS_QUERIES

    assert len(MEDIA_STACK_CATEGORIES) > 0
    assert "technology" in MEDIA_STACK_CATEGORIES

    assert len(RAPID_NEWS_SECTIONS) > 0
    assert "TECHNOLOGY" in RAPID_NEWS_SECTIONS

    assert len(SUBREDDITS) > 0
    assert "india" in SUBREDDITS

    assert len(NEWS_ORG_TOPICS) > 0
    assert "government_policy" in NEWS_ORG_TOPICS

    assert len(CORE_KEYWORDS) > 0
    assert "Artificial intelligence" in CORE_KEYWORDS


def test_pipeline_source_toggles(monkeypatch):
    from config import Config

    monkeypatch.setenv("DISABLED_PIPELINE_SOURCES", "reddit, rapid_news")
    monkeypatch.delenv("ENABLED_PIPELINE_SOURCES", raising=False)
    cfg = Config()

    assert cfg.is_source_enabled("gnews") is True
    assert cfg.is_source_enabled("reddit") is False
    assert cfg.is_source_enabled("rapid_news") is False

    monkeypatch.setenv("ENABLED_PIPELINE_SOURCES", "gnews, media_stack")
    cfg2 = Config()
    assert cfg2.is_source_enabled("gnews") is True
    assert cfg2.is_source_enabled("reddit") is False
    assert cfg2.is_source_enabled("media_stack") is True

