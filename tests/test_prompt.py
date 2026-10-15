"""Unit tests for the modern Prompt engine and prompt evaluation harness."""

import pytest
from pathlib import Path
from service.agents.prompt import Prompt
from service.agents.base import AgentProvider, CompletionResult
from tests.prompt_eval.run_eval import run_prompt_evaluation, load_samples


class DummyAgent(AgentProvider):
    def complete(self, system_prompt: str, user_prompt: str) -> CompletionResult:
        return CompletionResult(content=f"SYSTEM: {system_prompt}\nUSER: {user_prompt}")


def test_prompt_parsing_and_metadata():
    raw = """---
name: test_formatter
description: A test markdown prompt
---

# System
You are a test system.

# User
Format this: {{NEWS}}
"""
    prompt = Prompt(raw, is_content=True)
    assert prompt.metadata.get("name") == "test_formatter"
    assert prompt.metadata.get("description") == "A test markdown prompt"
    assert prompt.system == "You are a test system."
    assert prompt.user == "Format this: {{NEWS}}"


def test_prompt_fill_case_insensitive():
    raw = """# System
System instruction.

# User
Article: {{news}}
"""
    prompt = Prompt(raw, is_content=True)

    # Test uppercase keyword
    rendered1 = prompt.fill(NEWS="Breaking tech news")
    assert rendered1.user == "Article: Breaking tech news"

    # Test lowercase keyword
    rendered2 = prompt.fill(news="Breaking world news")
    assert rendered2.user == "Article: Breaking world news"

    # Test mixed case
    rendered3 = prompt.fill(News="Mixed news")
    assert rendered3.user == "Article: Mixed news"


def test_prompt_fill_with_dict_and_individual_keys():
    raw = """# System
News Extractor.

# User
{{NEWS}}
"""
    prompt = Prompt(raw, is_content=True)

    data = {
        "title": "Quantum Computing Milestone",
        "publication_date": "2026-09-12",
        "content": "Scientists achieved 1 million qubits.",
    }

    # Pass as dictionary
    rendered = prompt.fill(news=data)
    assert "Title: Quantum Computing Milestone" in rendered.user
    assert "Published: 2026-09-12" in rendered.user
    assert "Content:\nScientists achieved 1 million qubits." in rendered.user

    # Pass as individual keyword args
    rendered_kwargs = prompt.fill(**data)
    assert "Title: Quantum Computing Milestone" in rendered_kwargs.user
    assert "Published: 2026-09-12" in rendered_kwargs.user
    assert "Content:\nScientists achieved 1 million qubits." in rendered_kwargs.user


def test_prompt_str_coercion():
    raw = """# System
System block.

# User
User block: {{CONTENT}}
"""
    prompt = Prompt(raw, is_content=True).fill(content="Sample text")
    assert str(prompt) == "System block.\n\nUser block: Sample text"


def test_agent_complete_from_prompt_md(tmp_path: Path):
    template = tmp_path / "test_prompt.prompt.md"
    template.write_text(
        """---
name: unit_test
---
# System
You are an expert editor.

# User
Analyze: {{NEWS}}
""",
        encoding="utf-8",
    )

    agent = DummyAgent()
    result = agent.complete_from_template(template, {"news": "Test headline"})
    assert "SYSTEM: You are an expert editor." in result.content
    assert "USER: Analyze: Test headline" in result.content

    # Also test passing Prompt instance directly
    p_obj = Prompt(template)
    result_obj = agent.complete_from_template(p_obj, {"news": "Direct prompt obj"})
    assert "SYSTEM: You are an expert editor." in result_obj.content
    assert "USER: Analyze: Direct prompt obj" in result_obj.content


def test_prompt_eval_samples_and_dry_run():
    samples = load_samples()
    assert len(samples) >= 5

    results = run_prompt_evaluation(dry_run=True)
    assert results["total"] >= 5
    assert len(results["samples"]) == results["total"]
    assert results["samples"][0]["stage1"]["output"] == "[Dry run: LLM not called]"
    assert results["samples"][0]["stage2"]["output"] == "[Dry run: LLM not called]"
    assert results["samples"][0]["stage3"]["output"] == "[Dry run: LLM not called]"
