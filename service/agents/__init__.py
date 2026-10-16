"""
agents — Abstract agent layer for LLM completions.

Usage:
    from service.agents.factory import create_agent

    agent = create_agent()  # reads AGENT_PROVIDER env var
    result = agent.complete("You are a classifier.", "Is this news? ...")
    print(result.content)
"""

from .factory import create_agent
from .base import AgentProvider, CompletionResult, ToolCallingProvider, ToolDefinition, ToolCall, AgentMessage

__all__ = [
    "create_agent",
    "AgentProvider",
    "CompletionResult",
    "ToolCallingProvider",
    "ToolDefinition",
    "ToolCall",
    "AgentMessage",
]
