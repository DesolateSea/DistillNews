"""Light unit tests for LLM agent factory and template rendering using pytest."""

import pytest
from pathlib import Path
from agents.factory import create_agent
from agents.base import AgentProvider, CompletionResult


class DummyAgent(AgentProvider):
    def complete(self, system_prompt: str, user_prompt: str) -> CompletionResult:
        return CompletionResult(content=f"System: {system_prompt} | User: {user_prompt}")


def test_agent_factory_unknown_provider_raises_error():
    with pytest.raises(ValueError, match="Unknown agent provider: 'invalid_provider'"):
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
