from unittest.mock import MagicMock, patch

import pytest
from service.agents.base import AgentMessage


def test_scraper_redirect_is_revalidated_and_connection_pinned():
    from pipeline.scrapers.safe_fetch import fetch_public_html
    response = MagicMock(status=302)
    response.headers = {"Location": "https://127.0.0.1/secret"}
    pool = MagicMock()
    pool.urlopen.return_value = response
    def addresses(host, *args, **kwargs):
        return [(None, None, None, None, ("93.184.216.34" if host == "example.com" else "127.0.0.1", 443))]
    with patch("socket.getaddrinfo", side_effect=addresses), patch(
        "urllib3.HTTPSConnectionPool", return_value=pool) as factory:
        with pytest.raises(ValueError, match="Non-public"):
            fetch_public_html("https://example.com/news")
    assert factory.call_args.args[0] == "93.184.216.34"
    assert factory.call_args.kwargs["assert_hostname"] == "example.com"
    assert pool.urlopen.call_args.kwargs["redirect"] is False
    pool.close.assert_called_once()


def test_scraper_rejects_oversized_and_compressed_content():
    from pipeline.scrapers.safe_fetch import fetch_public_html
    response = MagicMock(status=200)
    pool = MagicMock()
    pool.urlopen.return_value = response
    dns = [(None, None, None, None, ("93.184.216.34", 443))]
    with patch("socket.getaddrinfo", return_value=dns), patch("urllib3.HTTPSConnectionPool", return_value=pool):
        response.headers = {"Content-Encoding": "gzip"}
        with pytest.raises(ValueError, match="Compressed"):
            fetch_public_html("https://example.com")
        response.headers = {}
        response.stream.return_value = [b"x" * 2_000_001]
        with pytest.raises(ValueError, match="resource limits"):
            fetch_public_html("https://example.com")


def test_chat_history_is_bounded_isolated_and_not_logged():
    from service.chatbot.service import ChatbotService
    agent = MagicMock()
    agent.chat_with_tools.return_value = AgentMessage(role="assistant", content="private reply")
    logger = MagicMock()
    chatbot = ChatbotService(agent, MagicMock(), logger=logger)
    chatbot.get_response("private user one", user_id="one")
    chatbot.get_response("private user two", user_id="two")
    messages = agent.chat_with_tools.call_args.args[0]
    assert "private user one" not in messages[0].content
    for i in range(1001):
        chatbot.get_response("hello", user_id=str(i))
    assert len(chatbot._user_memory) == 1000
    logger.chat_query.assert_not_called()
    logger.chat_response.assert_not_called()
    logger.ai_call.assert_not_called()


def test_ollama_uses_modern_provider_without_julep(monkeypatch):
    from service.agents.factory import create_agent
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://internal-model:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2")
    with patch("service.agents.providers.openai.OpenAIAgent") as provider:
        create_agent("ollama")
    provider.assert_called_once_with(api_key="ollama", model="llama3.2", base_url="http://internal-model:11434/v1")


def test_untrusted_html_does_not_read_local_files(tmp_path):
    from pipeline.parsers.paragraph_extractor import clean_html
    secret = tmp_path / "secret.html"
    secret.write_text("<p>secret contents</p>")
    from bs4 import MarkupResemblesLocatorWarning
    with pytest.warns(MarkupResemblesLocatorWarning):
        parsed, _ = clean_html(str(secret), debug=False)
    assert "secret contents" not in parsed["content"]
