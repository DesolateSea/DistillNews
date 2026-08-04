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
    agent = FakeToolCallingAgent()
    tool = ToolDefinition(name="test_tool", description="test", parameters={})
    
    messages = [AgentMessage(role="user", content="do something")]
    response1 = agent.chat_with_tools(messages, tools=[tool])
    
    assert response1.role == "assistant"
    assert response1.tool_calls is not None
    assert len(response1.tool_calls) == 1
    assert response1.tool_calls[0].name == "test_tool"
    
    messages.append(response1)
    messages.append(AgentMessage(role="tool", content="success", tool_call_id=response1.tool_calls[0].id))
    
    response2 = agent.chat_with_tools(messages, tools=[tool])
    assert response2.role == "assistant"
    assert response2.content == "final result"
