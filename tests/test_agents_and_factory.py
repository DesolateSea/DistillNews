"""Light unit tests for LLM agent factory and template rendering using pytest."""

import pytest
from pathlib import Path
from service.agents.factory import create_agent
from service.agents.base import (
    AgentProvider, 
    CompletionResult,
    ToolCallingProvider,
    ToolDefinition,
    ToolCall,
    AgentMessage
)
from service.agents.orchestrator import AgentOrchestrator


class DummyAgent(AgentProvider):
    def complete(self, system_prompt: str, user_prompt: str) -> CompletionResult:
        return CompletionResult(content=f"System: {system_prompt} | User: {user_prompt}")


class FakeToolCallingAgent(ToolCallingProvider):
    def complete(self, system_prompt: str, user_prompt: str) -> CompletionResult:
        return CompletionResult(content="dummy")

    def chat_with_tools(self, messages: list[AgentMessage], tools: list[ToolDefinition] | None = None, tool_choice: str | dict = "auto") -> AgentMessage:
        has_tool_call = any(m.role == "assistant" and m.tool_calls for m in messages)
        if not has_tool_call and tools:
            return AgentMessage(
                role="assistant",
                tool_calls=[ToolCall(id="call_123", name=tools[0].name, arguments={"arg": "val"})]
            )
        return AgentMessage(role="assistant", content="final result")


def test_agent_factory_unknown_provider_raises_error():
    with pytest.raises(ValueError, match="Available: openai"):
        create_agent("invalid_provider")


def test_template_render_substitution(tmp_path: Path):
    yaml_content = """
name: test_task
main:
  - prompt:
      - role: system
        content: "You are a test agent."
      - role: user
        content: "Is this news about {steps[0].input.topic}?"
"""
    template_file = tmp_path / "test_prompt.yaml"
    template_file.write_text(yaml_content, encoding="utf-8")

    sys_p, user_p = AgentProvider._render_template(template_file, {"topic": "AI technology"})
    assert sys_p == "You are a test agent."
    assert user_p == "Is this news about AI technology?"


def test_dummy_agent_complete_from_template(tmp_path: Path):
    yaml_content = """
name: test_task
main:
  - prompt:
      - role: system
        content: "System prompt"
      - role: user
        content: "Input: {steps[0].input.query}"
"""
    template_file = tmp_path / "test_prompt.yaml"
    template_file.write_text(yaml_content, encoding="utf-8")

    agent = DummyAgent()
    res = agent.complete_from_template(template_file, {"query": "Hello world"})
    assert res.content == "System: System prompt | User: Input: Hello world"


def test_tool_calling_provider_interface():
    tool = ToolDefinition(name="test", description="desc", parameters={"type": "object"})
    assert tool.name == "test"
    
    call = ToolCall(id="1", name="test", arguments={})
    assert call.id == "1"
    
    msg = AgentMessage(role="user", content="hello")
    assert msg.role == "user"
    
    agent = FakeToolCallingAgent()
    assert isinstance(agent, ToolCallingProvider)


def test_orchestrator_basic_flow():
    called = []
    def dummy_tool_fn(arg: str):
        called.append(arg)
        return {"status": "ok", "echo": arg}

    agent = FakeToolCallingAgent()
    tool = ToolDefinition(name="test_tool", description="test", parameters={})
    orchestrator = AgentOrchestrator(
        agent=agent,
        tools={"test_tool": (tool, dummy_tool_fn)},
        max_turns=3
    )

    result = orchestrator.run(user_prompt="do something", system_prompt="system prompt")
    assert result == "final result"
    assert called == ["val"]


def test_orchestrator_handles_unknown_tool():
    class UnknownToolAgent(ToolCallingProvider):
        def complete(self, system_prompt: str, user_prompt: str) -> CompletionResult:
            return CompletionResult(content="dummy")

        def chat_with_tools(self, messages: list[AgentMessage], tools: list[ToolDefinition] | None = None, tool_choice: str | dict = "auto") -> AgentMessage:
            has_tool_call = any(m.role == "assistant" and m.tool_calls for m in messages)
            if not has_tool_call:
                return AgentMessage(
                    role="assistant",
                    tool_calls=[ToolCall(id="call_999", name="non_existent_tool", arguments={})]
                )
            return AgentMessage(role="assistant", content="handled unknown tool")

    orchestrator = AgentOrchestrator(
        agent=UnknownToolAgent(),
        tools={},
        max_turns=3
    )

    # Should not raise KeyError
    result = orchestrator.run(user_prompt="trigger unknown tool", system_prompt="system")
    assert result == "handled unknown tool"
