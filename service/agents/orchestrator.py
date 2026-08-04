import json
from typing import Callable, Any
from service.agents.base import ToolCallingProvider, ToolDefinition, ToolCall, AgentMessage

class AgentOrchestrator:
    """Multi-turn agent loop that auto-executes tool calls returned by the LLM."""

    def __init__(
        self,
        agent: ToolCallingProvider,
        tools: dict[str, tuple[ToolDefinition, Callable[..., Any]]],
        max_turns: int = 5,
    ):
        self._agent = agent
        self._tools = tools  # name -> (schema, callable)
        self._max_turns = max_turns

    @property
    def tool_definitions(self) -> list[ToolDefinition]:
        return [schema for schema, _ in self._tools.values()]

    def run(self, user_prompt: str, system_prompt: str) -> str:
        messages = [
            AgentMessage(role="system", content=system_prompt),
            AgentMessage(role="user", content=user_prompt),
        ]

        for _ in range(self._max_turns):
            response = self._agent.chat_with_tools(
                messages, tools=self.tool_definitions
            )
            messages.append(response)

            if not response.tool_calls:
                return response.content or ""

            for call in response.tool_calls:
                _, fn = self._tools[call.name]
                try:
                    result = fn(**call.arguments)
                except Exception as e:
                    result = {"error": str(e)}
                messages.append(AgentMessage(
                    role="tool",
                    tool_call_id=call.id,
                    content=json.dumps(result) if not isinstance(result, str) else result,
                ))

        # Exhausted turns, return last assistant content
        for msg in reversed(messages):
            if msg.role == "assistant" and msg.content:
                return msg.content
        return ""
