"""Unit tests for standalone embedding_server microservice and pipeline/cli.py."""

import pytest
from click.testing import CliRunner
from embedding_server.app import app, EmbedRequest, EmbedManyRequest
from pipeline.cli import cli


class DummyModel:
    def encode(self, text_or_texts, **kwargs):
        if isinstance(text_or_texts, str):
            return [0.1, 0.2, 0.3]
        return [[0.1, 0.2, 0.3] for _ in text_or_texts]


def test_embedding_server_health():
    from fastapi.testclient import TestClient

    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "model" in data


def test_embedding_server_embed_endpoint(monkeypatch):
    from fastapi.testclient import TestClient
    import embedding_server.app as emb_app

    monkeypatch.setattr(emb_app, "get_model", lambda: DummyModel())

    client = TestClient(app)
    res = client.post("/embed", json={"text": "Hello world"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["embedding"]) == 3
    assert data["embedding"] == [0.1, 0.2, 0.3]


def test_embedding_server_embed_empty_text():
    from fastapi.testclient import TestClient

    client = TestClient(app)
    res = client.post("/embed", json={"text": ""})
    assert res.status_code == 200
    assert res.json() == {"embedding": []}


def test_embedding_server_embed_many_endpoint(monkeypatch):
    from fastapi.testclient import TestClient
    import embedding_server.app as emb_app

    monkeypatch.setattr(emb_app, "get_model", lambda: DummyModel())

    client = TestClient(app)
    res = client.post("/embed_many", json={"texts": ["Article 1", "Article 2"]})
    assert res.status_code == 200
    data = res.json()
    assert len(data["embeddings"]) == 2
    assert data["embeddings"][0] == [0.1, 0.2, 0.3]


def test_pipeline_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "DistillNews — AI-Powered News Aggregation Pipeline." in result.output
    assert "tui" in result.output


def test_pipeline_cli_tui_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["tui", "--help"])
    assert result.exit_code == 0
    assert "Launch the interactive TUI dashboard." in result.output


def test_pipeline_cli_invokes_tui(monkeypatch):
    import pipeline.cli as pcli
    launched = False

    def mock_launch():
        nonlocal launched
        launched = True

    monkeypatch.setattr(pcli, "_launch_tui", mock_launch)
    runner = CliRunner()
    result = runner.invoke(cli, [])
    assert result.exit_code == 0
    assert launched is True
