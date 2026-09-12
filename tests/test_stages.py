"""
Unit and integration tests for pipeline stages in pipeline/stages/.

Verifies:
  - parse stage dispatch and error handling
  - dedup stage duplicate detection and article_id attachment
  - classify stage gatekeeper logic (assured vs unassured)
  - extract stage structured output parsing
  - format_markdown stage
  - embed stage vector normalization
  - persist stage storage and metadata cleanup
  - End-to-end streaming execution of all stages together
"""

import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from pipeline.engine.stage import clear_registered_stages, stage
from pipeline.engine.stream import RawArticle
from pipeline.engine.task import DropArticle, PipelineContext, TaskState
from pipeline.engine.registry import StageRegistry
from pipeline.engine.runner import StreamingRunner
from service.agents.base import AgentProvider, CompletionResult
from service.blob.article_store import ArticleStore


class MockAgent(AgentProvider):
    def __init__(self, is_news_val: bool = True, extract_json: dict | None = None):
        self.is_news_val = is_news_val
        self.extract_json = extract_json or {
            "title": "Extracted Headline",
            "summary": "Brief summary",
            "category": "tech",
            "tags": ["ai", "python"],
            "content": "Full article content here.",
        }

    def complete(self, system_prompt: str, user_prompt: str) -> CompletionResult:
        return CompletionResult(content=json.dumps(self.extract_json))

    def complete_from_template(self, template_path: Path | str, context: dict) -> CompletionResult:
        path_str = str(template_path)
        if "is_news" in path_str:
            return CompletionResult(content="true" if self.is_news_val else "false")
        if "markdown_formatter" in path_str:
            return CompletionResult(content=f"# {context.get('content', '')}")
        return CompletionResult(content=json.dumps(self.extract_json))


class InMemoryArticleStore(ArticleStore):
    def __init__(self):
        self.store: dict[str, dict] = {}

    def article_exists(self, title_or_id: str, pub_date: str | int | float | None = None) -> bool:
        if pub_date is not None:
            aid = self.compute_article_id(title_or_id, pub_date)
            return aid in self.store
        return title_or_id in self.store

    def save_article(self, article_data: dict, article_id: str | None = None) -> str:
        aid = article_id or self.compute_article_id(
            article_data.get("title", ""), article_data.get("publication_date", "")
        )
        self.store[aid] = dict(article_data)
        return aid

    def load_article(self, article_id: str) -> dict | None:
        return self.store.get(article_id)

    def list_articles(self, limit: int | None = None) -> list[dict]:
        return [{"id": k, "title": v.get("title", "")} for k, v in self.store.items()]

    def load_all_articles(self, limit: int | None = None) -> list[dict]:
        return list(self.store.values())


@pytest.fixture(autouse=True)
def _clean_stages():
    clear_registered_stages()
    yield
    clear_registered_stages()


# ═══════════════════════════════════════════════════════════════════
# Stage-by-Stage Unit Tests
# ═══════════════════════════════════════════════════════════════════

class TestParseStage:
    def test_parse_core_item(self):
        from pipeline.stages.parse import parse

        raw = RawArticle(
            source="core",
            payload={"title": "Paper 1", "content": "Abstract text", "_assured_news": True},
        )
        result = parse(raw)
        assert result["title"] == "Paper 1"
        assert result["content"] == "Abstract text"
        assert result["_assured_news"] is True

    def test_parse_unknown_source_raises_drop(self):
        from pipeline.stages.parse import parse

        raw = RawArticle(source="unknown_xyz", payload={})
        with pytest.raises(DropArticle, match="No parser registered"):
            parse(raw)


class TestDedupStage:
    def test_dedup_drops_missing_title(self):
        from pipeline.stages.dedup import dedup

        ctx = PipelineContext(article_store=InMemoryArticleStore())
        with pytest.raises(DropArticle, match="No title available"):
            dedup({"title": ""}, ctx)

    def test_dedup_drops_existing_article(self):
        from pipeline.stages.dedup import dedup

        store = InMemoryArticleStore()
        aid = store.compute_article_id("Breaking News", "2026-09-12")
        store.store[aid] = {"title": "Breaking News"}

        ctx = PipelineContext(article_store=store)
        with pytest.raises(DropArticle, match="already exists"):
            dedup({"title": "Breaking News", "publication_date": "2026-09-12"}, ctx)

    def test_dedup_passes_new_article(self):
        from pipeline.stages.dedup import dedup

        store = InMemoryArticleStore()
        ctx = PipelineContext(article_store=store)
        item = {"title": "Brand New Post", "publication_date": "2026-09-12"}
        result = dedup(item, ctx)
        assert "_article_id" in result
        assert result["_article_id"] == store.compute_article_id("Brand New Post", "2026-09-12")


class TestClassifyStage:
    def test_assured_news_passes_without_agent(self):
        from pipeline.stages.classify import classify

        ctx = PipelineContext(agent=None)
        item = {"title": "GNews Report", "_assured_news": True}
        result = classify(item, ctx)
        assert result == item

    def test_unassured_news_classified_true_passes(self):
        from pipeline.stages.classify import classify

        ctx = PipelineContext(agent=MockAgent(is_news_val=True))
        item = {"title": "Reddit Real News", "_assured_news": False}
        result = classify(item, ctx)
        assert result == item

    def test_unassured_news_classified_false_dropped(self):
        from pipeline.stages.classify import classify

        ctx = PipelineContext(agent=MockAgent(is_news_val=False))
        item = {"title": "Reddit Meme / Spam", "_assured_news": False}
        with pytest.raises(DropArticle, match="Not a news post"):
            classify(item, ctx)


class TestExtractStage:
    def test_extract_enriches_structured_article(self):
        from pipeline.stages.extract import extract

        agent = MockAgent()
        ctx = PipelineContext(agent=agent)
        item = {
            "title": "Input Title",
            "content": "Input content",
            "_prompt": "news_from_html.prompt.md",
            "_article_id": "test1234",
            "_source_meta": {"source": "test_src"},
        }
        result = extract(item, ctx)
        assert result["title"] == "Extracted Headline"
        assert result["summary"] == "Brief summary"
        assert result["_article_id"] == "test1234"
        assert result["source"] == {"source": "test_src"}


class TestFormatMarkdownStage:
    def test_format_markdown_formats_content(self):
        from pipeline.stages.format import format_markdown

        agent = MockAgent()
        ctx = PipelineContext(agent=agent)
        item = {"content": "First line of content."}
        result = format_markdown(item, ctx)
        assert "markdown_content" in result
        assert "# First line of content." in result["markdown_content"]


class TestEmbedStage:
    def test_embed_generates_normalized_vector(self):
        from pipeline.stages.embed import embed

        mock_provider = MagicMock()
        mock_provider.embed_many.return_value = [[3.0, 4.0]]

        ctx = PipelineContext(extra={"embedding_provider": mock_provider})
        item = {"title": "Quantum Physics", "content": "Quantum entanglement."}
        result = embed(item, ctx)

        assert "embedding" in result
        assert len(result["embedding"]) == 2
        # L2 norm of [3, 4] is 5, so normalized is [0.6, 0.8]
        assert pytest.approx(result["embedding"][0]) == 0.6
        assert pytest.approx(result["embedding"][1]) == 0.8


class TestPersistStage:
    def test_persist_saves_to_store_and_cleans_metadata(self):
        from pipeline.stages.persist import persist

        store = InMemoryArticleStore()
        ctx = PipelineContext(article_store=store)

        item = {
            "title": "Final Article",
            "content": "Final content",
            "_article_id": "art_100",
            "_internal_flag": True,
        }
        saved = persist(item, ctx)

        assert saved["id"] == "art_100"
        assert "_internal_flag" not in saved
        assert "_article_id" not in saved
        assert store.load_article("art_100") is not None


# ═══════════════════════════════════════════════════════════════════
# End-to-End Streaming DAG Integration Test
# ═══════════════════════════════════════════════════════════════════

class TestEndToEndStreamingDAG:
    def test_full_pipeline_stream_execution(self):
        """
        Runs a complete end-to-end streaming DAG with a custom producer
        and all transform stages registered from pipeline.stages.
        """
        # Import transform stages
        from pipeline.stages.parse import parse
        from pipeline.stages.dedup import dedup
        from pipeline.stages.classify import classify
        from pipeline.stages.extract import extract
        from pipeline.stages.format import format_markdown
        from pipeline.stages.embed import embed
        from pipeline.stages.persist import persist

        # Define custom test producer that yields RawArticle items
        @stage
        def test_feed():
            yield RawArticle(
                source="core",
                payload={"title": "Article A", "content": "Content of article A", "_assured_news": True},
            )
            yield RawArticle(
                source="core",
                payload={"title": "Article B", "content": "Content of article B", "_assured_news": True},
            )

        reg = StageRegistry()
        reg.add(test_feed)
        reg.add(parse)
        reg.add(dedup)
        reg.add(classify)
        reg.add(extract)
        reg.add(format_markdown)
        reg.add(embed)
        reg.add(persist)

        store = InMemoryArticleStore()
        agent = MockAgent()
        mock_provider = MagicMock()
        mock_provider.embed_many.return_value = [[1.0, 0.0]]

        ctx = PipelineContext(
            agent=agent,
            article_store=store,
            extra={"embedding_provider": mock_provider},
        )

        runner = StreamingRunner(registry=reg, ctx=ctx, max_workers=2)
        runner.run()

        # Check all tasks
        all_tasks = runner.get_all_tasks()
        persist_tasks = [
            t for t in all_tasks if t.stage_name == "persist" and t.state == TaskState.DONE
        ]
        assert len(persist_tasks) == 2

        # Verify articles in store
        assert len(store.store) == 2

    def test_pipeline_runner_run_streaming_empty_or_disabled(self):
        """
        Verify PipelineRunner.run_streaming runs cleanly when sources are disabled or empty.
        """
        from pipeline.runner import PipelineRunner, StageStarted, StageCompleted
        events = []

        runner = PipelineRunner(callback=events.append)
        # Run streaming with no active sources
        runner.run_streaming(sources=[])

        stage_names = [e.stage for e in events if isinstance(e, (StageStarted, StageCompleted))]
        assert "fetch" in stage_names
        assert "scrape" in stage_names
        assert "generate" in stage_names
        assert "embed" in stage_names
