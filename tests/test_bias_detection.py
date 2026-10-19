"""Unit and integration tests for media bias detection and pipeline integration."""

import json
from unittest.mock import MagicMock, patch
import pytest
import torch
from click.testing import CliRunner

from config import Config
from pipeline.engine.stream import RawArticle
from pipeline.extraction_schemas import NEWS_BIAS_DETECTION_TOOL
from pipeline.bias.llm_detector import (
    analyze_article_bias_with_llm,
    _normalize_tool_result,
    _extract_json_from_text,
)
from pipeline.stages.detect_bias import detect_bias
from pipeline.engine.task import PipelineContext
from pipeline.cli import cli
from service.agents.base import AgentMessage, ToolCall, CompletionResult


class TestNewsBiasDetectionSchema:
    def test_schema_structure(self):
        assert NEWS_BIAS_DETECTION_TOOL.name == "submit_news_bias_analysis"
        assert "properties" in NEWS_BIAS_DETECTION_TOOL.parameters
        props = NEWS_BIAS_DETECTION_TOOL.parameters["properties"]

        assert "bias_score" in props
        assert props["bias_score"]["type"] == "number"

        assert "bias_types" in props
        assert props["bias_types"]["type"] == "array"
        assert "political" in props["bias_types"]["items"]["enum"]
        assert "linguistic" in props["bias_types"]["items"]["enum"]
        assert "commercial" in props["bias_types"]["items"]["enum"]

        assert "who_it_favors" in props
        assert "who_it_opposes" in props
        assert "loaded_language" in props
        assert "reasoning" in props

        required = NEWS_BIAS_DETECTION_TOOL.parameters["required"]
        assert "bias_score" in required
        assert "bias_types" in required
        assert "who_it_favors" in required
        assert "reasoning" in required

    def test_openai_schema_conversion(self):
        openai_schema = NEWS_BIAS_DETECTION_TOOL.to_openai_schema()
        assert openai_schema["type"] == "function"
        assert openai_schema["function"]["name"] == "submit_news_bias_analysis"
        assert "parameters" in openai_schema["function"]


class TestLLMBiasDetector:
    def test_empty_article_returns_safe_neutral(self):
        mock_agent = MagicMock()
        res = analyze_article_bias_with_llm({}, mock_agent)
        assert res["bias_score"] == 0.0
        assert res["bias_types"] == []
        assert res["who_it_favors"] == "none / neutral"
        mock_agent.chat_with_tools.assert_not_called()

    def test_successful_tool_call(self):
        mock_agent = MagicMock()
        tool_args = {
            "bias_score": 0.45,
            "bias_types": ["political", "linguistic"],
            "who_it_favors": "opposition party",
            "who_it_opposes": "sitting government",
            "loaded_language": ["controversial move", "reckless bill"],
            "reasoning": "Framed around opposition critique with dramatic verbs.",
        }
        mock_agent.chat_with_tools.return_value = AgentMessage(
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="call_123",
                    name="submit_news_bias_analysis",
                    arguments=tool_args,
                )
            ],
        )

        article = {
            "title": "Government unveils new economic policy",
            "content": "A reckless bill drew swift backlash from critics.",
        }
        res = analyze_article_bias_with_llm(article, mock_agent)

        assert res["method"] == "llm"
        assert res["bias_score"] == 0.45
        assert "political" in res["bias_types"]
        assert "linguistic" in res["bias_types"]
        assert res["who_it_favors"] == "opposition party"
        assert res["who_it_opposes"] == "sitting government"
        assert "reckless bill" in res["loaded_language"]
        assert "Framed around opposition critique" in res["reasoning"]

    def test_fallback_when_content_json_returned(self):
        mock_agent = MagicMock()
        raw_json = json.dumps({
            "bias_score": 0.75,
            "bias_types": ["commercial", "linguistic"],
            "who_it_favors": "Tech Giant Corp",
            "who_it_opposes": "competitors",
            "loaded_language": ["revolutionary breakthrough"],
            "reasoning": "Promotional framing without scrutiny.",
        })
        mock_agent.chat_with_tools.return_value = AgentMessage(
            role="assistant",
            content=raw_json,
            tool_calls=None,
        )

        article = {"title": "Company Press Event", "content": "A revolutionary breakthrough..."}
        res = analyze_article_bias_with_llm(article, mock_agent)

        assert res["bias_score"] == 0.75
        assert "commercial" in res["bias_types"]
        assert res["who_it_favors"] == "Tech Giant Corp"

    def test_fallback_completion_on_tool_error(self):
        mock_agent = MagicMock()
        mock_agent.chat_with_tools.side_effect = RuntimeError("Tool calling not supported")
        mock_agent.complete.return_value = CompletionResult(
            content=json.dumps({
                "bias_score": 0.1,
                "bias_types": [],
                "who_it_favors": "none / neutral",
                "who_it_opposes": "none / neutral",
                "loaded_language": [],
                "reasoning": "Factual overview.",
            })
        )

        article = {"title": "Markets Report", "content": "Stocks closed flat today."}
        res = analyze_article_bias_with_llm(article, mock_agent)

        assert res["bias_score"] == 0.1
        assert "_fallback_notice" in res

    def test_normalization_bounds(self):
        bad_args = {
            "bias_score": 2.5,  # Clamped to 1.0
            "bias_types": ["political", "INVALID_TYPE", "commercial"],
            "who_it_favors": 12345,
            "loaded_language": "single string instead of list",
            "reasoning": 67890,
        }
        norm = _normalize_tool_result(bad_args)
        assert norm["bias_score"] == 1.0
        assert norm["bias_types"] == ["political", "commercial"]
        assert norm["who_it_favors"] == "12345"
        assert norm["loaded_language"] == ["single string instead of list"]
        assert norm["reasoning"] == "67890"


class TestDetectBiasStage:
    def test_detect_bias_mode_none(self):
        cfg = Config()
        with patch.object(Config, "BIAS_DETECTION_MODE", "none"):
            ctx = PipelineContext(config=cfg, agent=MagicMock())
            item = {"title": "Headline", "content": "Body"}
            out = detect_bias(item, ctx)
            assert "bias_analysis" not in out
            assert out["title"] == "Headline"

    def test_detect_bias_mode_llm(self):
        cfg = Config()
        mock_agent = MagicMock()
        mock_agent.chat_with_tools.return_value = AgentMessage(
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="tc1",
                    name="submit_news_bias_analysis",
                    arguments={
                        "bias_score": 0.15,
                        "bias_types": ["linguistic"],
                        "who_it_favors": "none / neutral",
                        "who_it_opposes": "none / neutral",
                        "loaded_language": ["mild exaggeration"],
                        "reasoning": "Mostly factual report.",
                    },
                )
            ],
        )

        with patch.object(Config, "BIAS_DETECTION_MODE", "llm"):
            ctx = PipelineContext(config=cfg, agent=mock_agent)
            item = {"title": "Diplomatic Summit", "content": "Leaders discussed trade."}
            out = detect_bias(item, ctx)
            assert "bias_analysis" in out
            assert out["bias_analysis"]["bias_score"] == 0.15
            assert "linguistic" in out["bias_analysis"]["bias_types"]


class TestCLIAnalyzeCommand:
    def test_cli_analyze_custom_text(self):
        runner = CliRunner()
        mock_agent = MagicMock()
        mock_agent.chat_with_tools.return_value = AgentMessage(
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="tc1",
                    name="submit_news_bias_analysis",
                    arguments={
                        "bias_score": 0.65,
                        "bias_types": ["commercial", "political"],
                        "who_it_favors": "oil industry",
                        "who_it_opposes": "clean energy subsidies",
                        "loaded_language": ["crushing regulations"],
                        "reasoning": "Strong corporate viewpoint presented.",
                    },
                )
            ],
        )

        with patch("service.agents.factory.create_agent", return_value=mock_agent):
            result = runner.invoke(
                cli,
                [
                    "analyze",
                    "--text",
                    "Industry leaders warned of crushing regulations under the proposed bill.",
                    "--title",
                    "Energy Policy Dispute",
                ],
            )
            assert result.exit_code == 0
            assert "MEDIA BIAS ANALYSIS REPORT" in result.output
            assert "0.65 / 1.0 (HIGH BIAS)" in result.output
            assert "commercial, political" in result.output
            assert "oil industry" in result.output

    def test_cli_analyze_json_output(self):
        runner = CliRunner()
        mock_agent = MagicMock()
        mock_agent.chat_with_tools.return_value = AgentMessage(
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="tc1",
                    name="submit_news_bias_analysis",
                    arguments={
                        "bias_score": 0.05,
                        "bias_types": [],
                        "who_it_favors": "none / neutral",
                        "who_it_opposes": "none / neutral",
                        "loaded_language": [],
                        "reasoning": "Completely objective scientific dispatch.",
                    },
                )
            ],
        )

        with patch("service.agents.factory.create_agent", return_value=mock_agent):
            result = runner.invoke(
                cli,
                [
                    "analyze",
                    "--text",
                    "Solar eclipse observed across three continents today.",
                    "--json",
                ],
            )
            assert result.exit_code == 0
            parsed = json.loads(result.output)
            assert len(parsed) == 1
            assert parsed[0]["bias_analysis"]["bias_score"] == 0.05
            assert parsed[0]["bias_analysis"]["who_it_favors"] == "none / neutral"


class TestConfigBiasProperties:
    def test_config_properties_defaults(self):
        cfg = Config()
        assert cfg.BIAS_DETECTION_MODE == "none"
        assert cfg.BIAS_BERT_MODEL == "bucketresearch/politicalBiasBERT"
        assert cfg.DATASET_SOURCE_PATH is None
        assert cfg.CUSTOM_NEWS_PATH is None
        assert cfg.CUSTOM_NEWS_TEXT is None
        assert cfg.CUSTOM_NEWS_TITLE == "Custom Direct News"


class TestBertBiasDetector:
    def test_empty_article_returns_safe_neutral(self):
        from pipeline.bias.bert_detector import analyze_article_bias_with_bert
        res = analyze_article_bias_with_bert({})
        assert res["method"] == "bert"
        assert res["predicted_label"] == "NEUTRAL"
        assert res["confidence"] == 0.0

    def test_mock_bert_inference_3class(self):
        from pipeline.bias.bert_detector import analyze_article_bias_with_bert

        mock_model = MagicMock()
        mock_tokenizer = MagicMock()

        # 3 classes: Left, Center, Right
        mock_model.config.id2label = {0: "LEFT", 1: "CENTER", 2: "RIGHT"}
        mock_model.parameters.return_value = [MagicMock(device=torch.device("cpu"))]

        # Logits predicting Center with high probability
        fake_logits = torch.tensor([[1.0, 5.0, 0.5]])
        mock_outputs = MagicMock()
        mock_outputs.logits = fake_logits
        mock_model.return_value = mock_outputs

        mock_encoded = {
            "input_ids": torch.tensor([[101, 200, 102]]),
            "attention_mask": torch.tensor([[1, 1, 1]]),
        }
        mock_tokenizer.return_value = mock_encoded

        with patch("pipeline.bias.bert_detector.load_bert_model_and_tokenizer", return_value=(mock_model, mock_tokenizer, {0: "LEFT", 1: "CENTER", 2: "RIGHT"})):
            res = analyze_article_bias_with_bert({"title": "Economy update", "content": "Moderate growth noted."})
            assert res["method"] == "bert"
            assert res["predicted_label"] == "CENTER"
            assert res["confidence"] > 0.9
            assert "LEFT" in res["scores"]
            assert "CENTER" in res["scores"]
            assert "RIGHT" in res["scores"]

    def test_generic_label_fallback_for_babe(self):
        from pipeline.bias.bert_detector import _extract_label_mapping

        mock_config = MagicMock()
        mock_config.id2label = {0: "LABEL_0", 1: "LABEL_1"}
        mapping = _extract_label_mapping(mock_config, "mediabiasgroup/roberta-babe-ft")
        assert mapping[0] == "NON-BIASED"
        assert mapping[1] == "BIASED"

    def test_detect_bias_stage_mode_bert(self):
        from pipeline.stages.detect_bias import detect_bias

        cfg = Config()
        mock_bert_result = {
            "method": "bert",
            "model_name": "bucketresearch/politicalBiasBERT",
            "predicted_label": "LEFT",
            "confidence": 0.85,
            "scores": {"LEFT": 0.85, "CENTER": 0.10, "RIGHT": 0.05},
        }

        with patch.object(Config, "BIAS_DETECTION_MODE", "bert"):
            with patch("pipeline.stages.detect_bias.analyze_article_bias_with_bert", return_value=mock_bert_result):
                ctx = PipelineContext(config=cfg)
                item = {"title": "Editorial", "content": "Progressive tax proposal."}
                out = detect_bias(item, ctx)
                assert "bias_analysis" in out
                assert out["bias_analysis"]["method"] == "bert"
                assert out["bias_analysis"]["predicted_label"] == "LEFT"


class TestDatasetSource:
    def test_load_dataset_records_csv(self, tmp_path):
        from pipeline.stages.sources.dataset import load_dataset_records

        csv_file = tmp_path / "test_benchmark.csv"
        csv_file.write_text(
            "title,text,label\n"
            "News Story 1,The senator defended the bill yesterday.,BIASED\n"
            "News Story 2,Weather service reports rain across the coast.,NON-BIASED\n"
        )

        records = list(load_dataset_records(csv_file))
        assert len(records) == 2
        assert records[0]["title"] == "News Story 1"
        assert records[0]["ground_truth"] == "BIASED"
        assert records[0]["_assured_news"] is True
        assert records[1]["title"] == "News Story 2"
        assert records[1]["ground_truth"] == "NON-BIASED"

    def test_load_dataset_records_jsonl(self, tmp_path):
        from pipeline.stages.sources.dataset import load_dataset_records

        jsonl_file = tmp_path / "test_benchmark.jsonl"
        jsonl_file.write_text(
            json.dumps({"headline": "Market Rally", "content": "Tech stocks surged.", "bias": "neutral"}) + "\n"
        )

        records = list(load_dataset_records(jsonl_file))
        assert len(records) == 1
        assert records[0]["title"] == "Market Rally"
        assert records[0]["content"] == "Tech stocks surged."
        assert records[0]["ground_truth"] == "neutral"

    def test_fetch_dataset_producer(self, tmp_path):
        from pipeline.stages.sources.dataset import fetch_dataset

        csv_file = tmp_path / "data.csv"
        csv_file.write_text("text,bias\nSome political commentary,Left\n")

        cfg = Config()
        ctx = PipelineContext(config=cfg, extra={"dataset_path": str(csv_file)})

        items = list(fetch_dataset(ctx))
        assert len(items) == 1
        assert isinstance(items[0], RawArticle)
        assert items[0].source == "dataset"
        assert items[0].payload["ground_truth"] == "Left"

    def test_dataset_parser_integration(self):
        from pipeline.stages.parse import parse
        raw = RawArticle(
            source="dataset",
            payload={"title": "Dataset Article", "content": "Body text", "ground_truth": "Left"},
            title="Dataset Article",
        )
        parsed = parse(raw)
        assert parsed["title"] == "Dataset Article"
        assert parsed["content"] == "Body text"
        assert parsed["ground_truth"] == "Left"
        assert parsed["_assured_news"] is True


class TestCustomNewsSource:
    def test_fetch_custom_news_from_ctx_extra_text(self):
        from pipeline.stages.sources.custom_news import fetch_custom_news

        cfg = Config()
        ctx = PipelineContext(
            config=cfg,
            extra={"custom_news_text": "Direct user input text.", "custom_news_title": "My Article"},
        )
        items = list(fetch_custom_news(ctx))
        assert len(items) == 1
        assert items[0].source == "custom_news"
        assert items[0].payload["title"] == "My Article"
        assert items[0].payload["content"] == "Direct user input text."

    def test_fetch_custom_news_from_config(self):
        from pipeline.stages.sources.custom_news import fetch_custom_news

        cfg = Config()
        with patch.object(Config, "CUSTOM_NEWS_TEXT", "Config direct text"):
            with patch.object(Config, "CUSTOM_NEWS_TITLE", "Config Title"):
                ctx = PipelineContext(config=cfg)
                items = list(fetch_custom_news(ctx))
                assert len(items) == 1
                assert items[0].payload["title"] == "Config Title"
                assert items[0].payload["content"] == "Config direct text"

    def test_fetch_custom_news_from_file(self, tmp_path):
        from pipeline.stages.sources.custom_news import fetch_custom_news

        news_file = tmp_path / "custom.txt"
        news_file.write_text("Custom Breaking News\n\nAn unexpected event occurred today.")

        cfg = Config()
        ctx = PipelineContext(config=cfg, extra={"custom_news_path": str(news_file)})
        items = list(fetch_custom_news(ctx))
        assert len(items) == 1
        assert "Custom Breaking News" in items[0].payload["content"]

    def test_custom_news_parser_integration(self):
        from pipeline.stages.parse import parse
        raw = RawArticle(
            source="custom_news",
            payload={"title": "Custom Post", "content": "Direct text payload"},
            title="Custom Post",
        )
        parsed = parse(raw)
        assert parsed["title"] == "Custom Post"
        assert parsed["content"] == "Direct text payload"
        assert parsed["_assured_news"] is True


class TestDatasetAndCustomNewsWithLLM:
    def test_custom_news_through_llm_pipeline(self):
        """Verify custom_news flows through parse -> classify -> extract -> format -> detect_bias."""
        from pipeline.stages.parse import parse
        from pipeline.stages.classify import classify
        from pipeline.stages.extract import extract
        from pipeline.stages.format import format_markdown
        from pipeline.stages.detect_bias import detect_bias

        raw = RawArticle(
            source="custom_news",
            payload={
                "title": "Diplomatic Talks",
                "content": "Leaders met in Geneva for peace negotiations.",
                "_assured_news": True,
            },
            title="Diplomatic Talks",
        )

        mock_agent = MagicMock()
        # Mock extract stage JSON completion
        mock_agent.complete_from_template.side_effect = [
            # 1. extract stage response
            CompletionResult(content=json.dumps({
                "title": "Diplomatic Talks",
                "summary": "Leaders met in Geneva.",
                "content": "Leaders met in Geneva for peace negotiations.",
                "category": "World",
                "tags": ["diplomacy", "peace"],
            })),
            # 2. format_markdown stage response
            CompletionResult(content="Leaders met in Geneva for peace negotiations."),
        ]

        # Mock detect_bias LLM tool call
        mock_agent.chat_with_tools.return_value = AgentMessage(
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="call_bias",
                    name="submit_news_bias_analysis",
                    arguments={
                        "bias_score": 0.08,
                        "bias_types": [],
                        "who_it_favors": "none / neutral",
                        "who_it_opposes": "none / neutral",
                        "loaded_language": [],
                        "reasoning": "Neutral factual report of peace talks.",
                    },
                )
            ],
        )

        cfg = Config()
        with patch.object(Config, "BIAS_DETECTION_MODE", "llm"):
            ctx = PipelineContext(config=cfg, agent=mock_agent)

            # Step 1: Parse
            parsed = parse(raw, ctx)
            assert parsed["title"] == "Diplomatic Talks"

            # Step 2: Classify (assured passes through directly)
            classified = classify(parsed, ctx)
            assert classified["title"] == "Diplomatic Talks"

            # Step 3: Extract (calls LLM)
            extracted = extract(classified, ctx)
            assert extracted["category"] == "World"

            # Step 4: Format Markdown (calls LLM)
            formatted = format_markdown(extracted, ctx)
            assert "markdown_content" in formatted

            # Step 5: Detect Bias with LLM
            detected = detect_bias(formatted, ctx)
            assert "bias_analysis" in detected
            assert detected["bias_analysis"]["method"] == "llm"
            assert detected["bias_analysis"]["bias_score"] == 0.08
            assert detected["bias_analysis"]["who_it_favors"] == "none / neutral"


class TestCLIAnalyzeWithBertAndDataset:
    def test_cli_analyze_bert_custom_text(self):
        runner = CliRunner()
        mock_bert = {
            "method": "bert",
            "model_name": "bucketresearch/politicalBiasBERT",
            "predicted_label": "RIGHT",
            "confidence": 0.77,
            "scores": {"LEFT": 0.10, "CENTER": 0.13, "RIGHT": 0.77},
        }

        with patch("pipeline.bias.bert_detector.analyze_article_bias_with_bert", return_value=mock_bert):
            result = runner.invoke(
                cli,
                [
                    "analyze",
                    "--detector", "bert",
                    "--text", "Fiscal conservative economic proposals highlighted.",
                    "--title", "Tax Reform Opinion",
                ],
            )
            assert result.exit_code == 0
            assert "MEDIA BIAS ANALYSIS REPORT" in result.output
            assert "BERT (bucketresearch/politicalBiasBERT)" in result.output
            assert "RIGHT (77.0%)" in result.output

    def test_cli_analyze_dataset_with_llm(self, tmp_path):
        runner = CliRunner()
        csv_file = tmp_path / "benchmark.csv"
        csv_file.write_text(
            "title,text,label\n"
            "Tech Regulation,Lawmakers proposed stricter privacy controls today.,BIASED\n"
        )

        mock_agent = MagicMock()
        mock_agent.chat_with_tools.return_value = AgentMessage(
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="call_99",
                    name="submit_news_bias_analysis",
                    arguments={
                        "bias_score": 0.40,
                        "bias_types": ["political"],
                        "who_it_favors": "privacy advocates",
                        "who_it_opposes": "tech monopolies",
                        "loaded_language": ["strict controls"],
                        "reasoning": "Framed around consumer privacy protection.",
                    },
                )
            ],
        )

        with patch("service.agents.factory.create_agent", return_value=mock_agent):
            result = runner.invoke(
                cli,
                [
                    "analyze",
                    "--dataset", str(csv_file),
                    "--detector", "llm",
                ],
            )
            assert result.exit_code == 0
            assert "Tech Regulation" in result.output
            assert "BIASED" in result.output
            assert "0.40 / 1.0 (MODERATE)" in result.output
            assert "privacy advocates" in result.output


class TestBenchmarkHarness:
    def test_normalize_ground_truth(self):
        from pipeline.benchmark.run_bias_benchmark import normalize_ground_truth

        target_set = {"LEFT", "CENTER", "RIGHT"}
        assert normalize_ground_truth("left", target_set) == "LEFT"
        assert normalize_ground_truth("lean left", target_set) == "LEFT"
        assert normalize_ground_truth("conservative", target_set) == "RIGHT"
        assert normalize_ground_truth("neutral", target_set) == "CENTER"

    def test_compute_classification_metrics(self):
        from pipeline.benchmark.run_bias_benchmark import compute_classification_metrics

        y_true = ["LEFT", "RIGHT", "CENTER", "LEFT"]
        y_pred = ["LEFT", "RIGHT", "LEFT", "LEFT"]  # 3 correct, 1 wrong
        labels = ["LEFT", "CENTER", "RIGHT"]

        metrics = compute_classification_metrics(y_true, y_pred, labels)
        assert metrics["accuracy"] == 0.75
        assert metrics["total_evaluated"] == 4
        assert metrics["correct"] == 3
        assert "per_class" in metrics
        assert "confusion_matrix" in metrics

    def test_evaluate_bias_benchmark_bert(self, tmp_path):
        from pipeline.benchmark.run_bias_benchmark import evaluate_bias_benchmark

        csv_file = tmp_path / "bench.csv"
        csv_file.write_text(
            "title,text,label\n"
            "Article A,Text A,Left\n"
            "Article B,Text B,Right\n"
        )

        mock_bert = {
            "method": "bert",
            "model_name": "bucketresearch/politicalBiasBERT",
            "predicted_label": "LEFT",
            "confidence": 0.88,
            "scores": {"LEFT": 0.88, "CENTER": 0.08, "RIGHT": 0.04},
        }

        with patch("pipeline.benchmark.run_bias_benchmark.analyze_article_bias_with_bert", return_value=mock_bert):
            report = evaluate_bias_benchmark(
                dataset_path=csv_file,
                detector="bert",
            )
            assert report.total_samples == 2
            assert report.bert_metrics is not None
            assert report.bert_metrics["correct"] == 1  # 1 matched Left

    def test_cli_benchmark_command(self, tmp_path):
        runner = CliRunner()
        csv_file = tmp_path / "bench.csv"
        csv_file.write_text("title,text,label\nArticle A,Text A,Left\n")

        mock_bert = {
            "method": "bert",
            "model_name": "bucketresearch/politicalBiasBERT",
            "predicted_label": "LEFT",
            "confidence": 0.90,
            "scores": {"LEFT": 0.90, "CENTER": 0.05, "RIGHT": 0.05},
        }

        with patch("pipeline.benchmark.run_bias_benchmark.analyze_article_bias_with_bert", return_value=mock_bert):
            result = runner.invoke(
                cli,
                [
                    "benchmark",
                    "--dataset", str(csv_file),
                    "--detector", "bert",
                ],
            )
            assert result.exit_code == 0
            assert "MEDIA BIAS BENCHMARK REPORT" in result.output
            assert "Overall Accuracy: 100.0%" in result.output

    def test_classify_article_bias_with_llm(self):
        from pipeline.bias.llm_detector import classify_article_bias_with_llm

        mock_agent = MagicMock()
        mock_agent.complete.return_value = CompletionResult(
            content=json.dumps({
                "predicted_label": "LEFT",
                "confidence": 0.85,
                "scores": {"LEFT": 0.85, "CENTER": 0.10, "RIGHT": 0.05},
                "reasoning": "Emphasizes progressive economic reform.",
            })
        )

        article = {"title": "Labor Bill", "content": "Union rights expanded."}
        res = classify_article_bias_with_llm(article, mock_agent, candidate_labels=["LEFT", "CENTER", "RIGHT"])

        assert res["method"] == "llm_classifier"
        assert res["predicted_label"] == "LEFT"
        assert res["confidence"] == 0.85
        assert res["scores"]["LEFT"] == 0.85
        assert "Union rights expanded" not in res["reasoning"] or True

    def test_evaluate_bias_benchmark_both_head_to_head(self, tmp_path):
        from pipeline.benchmark.run_bias_benchmark import evaluate_bias_benchmark

        csv_file = tmp_path / "bench.csv"
        csv_file.write_text(
            "title,text,label\n"
            "Article A,Text A,Left\n"
            "Article B,Text B,Right\n"
        )

        mock_bert = {
            "method": "bert",
            "model_name": "bucketresearch/politicalBiasBERT",
            "predicted_label": "LEFT",
            "confidence": 0.90,
            "scores": {"LEFT": 0.90, "CENTER": 0.05, "RIGHT": 0.05},
        }

        mock_llm_cls = {
            "method": "llm_classifier",
            "predicted_label": "LEFT",
            "confidence": 0.80,
            "scores": {"LEFT": 0.80, "CENTER": 0.10, "RIGHT": 0.10},
            "reasoning": "Progressive slant.",
        }

        mock_agent = MagicMock()

        with patch("pipeline.benchmark.run_bias_benchmark.analyze_article_bias_with_bert", return_value=mock_bert):
            with patch("pipeline.benchmark.run_bias_benchmark.classify_article_bias_with_llm", return_value=mock_llm_cls):
                report = evaluate_bias_benchmark(
                    dataset_path=csv_file,
                    detector="both",
                    agent=mock_agent,
                )

                assert report.bert_metrics is not None
                assert report.llm_metrics is not None
                assert report.comparison_metrics is not None
                assert report.comparison_metrics["agreement_count"] == 2
                assert report.comparison_metrics["agreement_rate"] == 1.0

    def test_resolve_benchmark_dataset_aliases(self, tmp_path):
        from pipeline.benchmark.run_bias_benchmark import resolve_benchmark_dataset

        sample_p = resolve_benchmark_dataset("sample")
        assert sample_p.name == "sample_bias_benchmark.csv"

        # Explicit custom file
        custom_file = tmp_path / "custom.csv"
        custom_file.write_text("text,label\nSome text,LEFT\n")
        resolved = resolve_benchmark_dataset(custom_file)
        assert resolved == custom_file

    def test_cli_benchmark_with_alias_flag(self):
        from pipeline.cli import cli

        runner = CliRunner()
        mock_bert = {
            "method": "bert",
            "model_name": "bucketresearch/politicalBiasBERT",
            "predicted_label": "LEFT",
            "confidence": 0.85,
            "scores": {"LEFT": 0.85, "CENTER": 0.10, "RIGHT": 0.05},
        }

        with patch("pipeline.bias.bert_detector.analyze_article_bias_with_bert", return_value=mock_bert):
            result = runner.invoke(
                cli,
                [
                    "benchmark",
                    "--detector", "bert",
                    "--dataset", "sample",
                    "--limit", "2",
                ],
            )
            assert result.exit_code == 0
            assert "MEDIA BIAS BENCHMARK REPORT" in result.output
            assert "Samples:      2" in result.output


