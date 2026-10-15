"""Unit tests for MCP server, AgentOrchestrator edge cases, and tool-calling providers."""

import json
from unittest.mock import MagicMock, patch
import pytest

from service.agents.base import (
    AgentMessage,
    CompletionResult,
    ToolCall,
    ToolDefinition,
    ToolCallingProvider,
)
from service.agents.orchestrator import AgentOrchestrator
from service.agents.providers.openai import OpenAIAgent
from service.chatbot.service import ChatbotService
from service.rag.base import DocumentStore, SearchResult
from mcp_server.app import mcp, list_categories, news_search, get_article, get_article_count
from pipeline.extraction_schemas import (
    ARTICLE_EXTRACTION_TOOL,
    NEWS_CLASSIFICATION_TOOL,
    MARKDOWN_FORMAT_TOOL,
)


# ----------------------------------------------------------------------
# 1. AgentOrchestrator Tests (Edge Cases & Resilience)
# ----------------------------------------------------------------------

def test_orchestrator_exhausted_turns_returns_last_assistant_content():
    class LoopingToolAgent(ToolCallingProvider):
        def complete(self, system_prompt: str, user_prompt: str) -> CompletionResult:
            return CompletionResult(content="fallback")

        def chat_with_tools(
            self,
            messages: list[AgentMessage],
            tools: list[ToolDefinition] | None = None,
            tool_choice: str | dict = "auto",
        ) -> AgentMessage:
            return AgentMessage(
                role="assistant",
                content="Partial synthesis before loop limit",
                tool_calls=[ToolCall(id="call_loop", name="ping", arguments={})],
            )

    orchestrator = AgentOrchestrator(
        agent=LoopingToolAgent(),
        tools={"ping": (ToolDefinition(name="ping", description="", parameters={}), lambda: "pong")},
        max_turns=3,
    )

    result = orchestrator.run(user_prompt="start", system_prompt="system")
    assert result == "Partial synthesis before loop limit"


def test_orchestrator_tool_exception_captured_gracefully():
    calls = []

    def failing_tool():
        raise RuntimeError("External service connection timeout")

    class RecoveryAgent(ToolCallingProvider):
        def complete(self, system_prompt: str, user_prompt: str) -> CompletionResult:
            return CompletionResult(content="fallback")

        def chat_with_tools(
            self,
            messages: list[AgentMessage],
            tools: list[ToolDefinition] | None = None,
            tool_choice: str | dict = "auto",
        ) -> AgentMessage:
            tool_messages = [m for m in messages if m.role == "tool"]
            if not tool_messages:
                return AgentMessage(
                    role="assistant",
                    tool_calls=[ToolCall(id="call_fail", name="failing_tool", arguments={})],
                )
            calls.append(tool_messages[0].content)
            return AgentMessage(role="assistant", content="Handled tool failure cleanly")

    tool = ToolDefinition(name="failing_tool", description="", parameters={})
    orchestrator = AgentOrchestrator(
        agent=RecoveryAgent(),
        tools={"failing_tool": (tool, failing_tool)},
        max_turns=3,
    )

    result = orchestrator.run(user_prompt="test error", system_prompt="system")
    assert result == "Handled tool failure cleanly"
    assert len(calls) == 1
    assert "External service connection timeout" in calls[0]


# ----------------------------------------------------------------------
# 2. OpenAI Provider Safe Argument Parsing & Formatting
# ----------------------------------------------------------------------

def test_openai_chat_with_tools_handles_malformed_arguments():
    agent = OpenAIAgent(api_key="fake-key", model="gpt-4o-mini")
    mock_client = MagicMock()

    mock_choice = MagicMock()
    mock_tc = MagicMock()
    mock_tc.id = "call_bad_json"
    mock_tc.function.name = "broken_tool"
    mock_tc.function.arguments = "{not: valid json"
    mock_choice.message.role = "assistant"
    mock_choice.message.content = None
    mock_choice.message.tool_calls = [mock_tc]

    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])
    agent._client = mock_client

    messages = [AgentMessage(role="user", content="hello")]
    res = agent.chat_with_tools(messages)

    assert res.role == "assistant"
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0].name == "broken_tool"
    assert res.tool_calls[0].arguments == {"raw_arguments": "{not: valid json"}


def test_openai_chat_with_tools_formats_prior_tool_calls_and_responses():
    agent = OpenAIAgent(api_key="fake-key", model="gpt-4o-mini")
    mock_client = MagicMock()

    mock_choice = MagicMock()
    mock_choice.message.role = "assistant"
    mock_choice.message.content = "Finished"
    mock_choice.message.tool_calls = None
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])
    agent._client = mock_client

    messages = [
        AgentMessage(role="system", content="System instruction"),
        AgentMessage(role="user", content="Find news"),
        AgentMessage(
            role="assistant",
            tool_calls=[ToolCall(id="call_1", name="search", arguments={"query": "test"})],
        ),
        AgentMessage(role="tool", tool_call_id="call_1", content='[{"title": "News 1"}]'),
    ]

    res = agent.chat_with_tools(messages)
    assert res.content == "Finished"

    sent_messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
    assert sent_messages[0] == {"role": "system", "content": "System instruction"}
    assert sent_messages[1] == {"role": "user", "content": "Find news"}
    assert sent_messages[2]["role"] == "assistant"
    assert sent_messages[2]["tool_calls"][0]["id"] == "call_1"
    assert sent_messages[3] == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": '[{"title": "News 1"}]',
    }


# ----------------------------------------------------------------------
# 3. ChatbotService Reader Context Mode
# ----------------------------------------------------------------------

def test_chatbot_reader_context_mode():
    class ReaderContextAgent(ToolCallingProvider):
        def __init__(self):
            self.last_messages = []

        def complete(self, system_prompt: str, user_prompt: str) -> CompletionResult:
            return CompletionResult(content="dummy")

        def chat_with_tools(
            self,
            messages: list[AgentMessage],
            tools: list[ToolDefinition] | None = None,
            tool_choice: str | dict = "auto",
        ) -> AgentMessage:
            self.last_messages = messages
            return AgentMessage(role="assistant", content="Answer about specific article")

    class MockArticleStore:
        def get_article(self, article_id: str):
            if article_id == "art-123":
                return {
                    "id": "art-123",
                    "title": "Quantum Computing Breakthrough",
                    "content": "Full article about quantum processors.",
                    "category": "Technology",
                }
            return None

    agent = ReaderContextAgent()
    doc_store = MagicMock(spec=DocumentStore)

    chatbot = ChatbotService(
        agent=agent,
        document_store=doc_store,
    )

    response = chatbot.get_response(
        "Summarize this article",
        user_id="user-1",
        reading="Title: Quantum Computing Breakthrough\nContent: Full article about quantum processors.",
    )
    assert response == "Answer about specific article"
    assert len(agent.last_messages) >= 2
    system_msg = agent.last_messages[0].content
    assert "Quantum Computing Breakthrough" in system_msg
    assert "Full article about quantum processors" in system_msg


# ----------------------------------------------------------------------
# 4. MCP Server Tools & Compatibility Wrapper
# ----------------------------------------------------------------------

def test_mcp_list_categories():
    cats = list_categories()
    assert isinstance(cats, list)
    assert "Technology" in cats
    assert "World" in cats
    assert "Business" in cats


def test_mcp_tools_with_mocked_backends():
    with patch("mcp_server.tools.search.search_news") as mock_search:
        mock_search.return_value = [{"title": "Test Title", "score": 0.95}]
        results = news_search(query="tech", limit=2)
        assert results == [{"title": "Test Title", "score": 0.95}]
        mock_search.assert_called_once_with(query="tech", limit=2, category=None)

    with patch("mcp_server.tools.articles.fetch_article") as mock_fetch:
        mock_fetch.return_value = {"id": "art-1", "title": "Headline"}
        article = get_article(article_id="art-1")
        assert article["title"] == "Headline"
        mock_fetch.assert_called_once_with(article_id="art-1")

    with patch("mcp_server.tools.articles.count_articles") as mock_count:
        mock_count.return_value = {"count": 42}
        count = get_article_count()
        assert count == {"count": 42}
        mock_count.assert_called_once()


# ----------------------------------------------------------------------
# 5. Extraction Schemas
# ----------------------------------------------------------------------

def test_extraction_schema_definitions():
    assert ARTICLE_EXTRACTION_TOOL.name == "submit_extracted_article"
    params = ARTICLE_EXTRACTION_TOOL.parameters
    assert params["type"] == "object"
    assert "title" in params["properties"]
    assert "content" in params["properties"]
    assert "category" in params["properties"]
    assert set(params["required"]).issubset(set(params["properties"].keys()))

    assert NEWS_CLASSIFICATION_TOOL.name == "submit_classification"
    assert "is_news" in NEWS_CLASSIFICATION_TOOL.parameters["properties"]

    assert MARKDOWN_FORMAT_TOOL.name == "submit_formatted_content"
    assert "markdown" in MARKDOWN_FORMAT_TOOL.parameters["properties"]
