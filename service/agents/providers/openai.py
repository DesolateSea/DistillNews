"""OpenAI-compatible agent provider.

Uses the OpenAI Python SDK for chat completions. This also supports
Microsoft Foundry's OpenAI-compatible ``/openai/v1`` endpoint with an API
key, as well as other compatible services.
"""

import os
import json
from config import config
from service.agents.base import ToolCallingProvider, CompletionResult, ToolDefinition, ToolCall, AgentMessage


class OpenAIAgent(ToolCallingProvider):
    """AgentProvider backed by an OpenAI-compatible chat completions API.

    Constructor args can override env-var defaults via config.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ):
        from openai import OpenAI  # defer import so the SDK is optional

        self._api_key = api_key or config.OPENAI_API_KEY
        self._model = model or config.OPENAI_MODEL
        self._base_url = base_url or config.OPENAI_BASE_URL

        if not self._api_key:
            raise ValueError("An API key is required. Set FOUNDRY_API_KEY or OPENAI_API_KEY.")

        client_kwargs: dict = {"api_key": self._api_key}
        if self._base_url:
            client_kwargs["base_url"] = self._base_url

        self._client = OpenAI(**client_kwargs)

    # ------------------------------------------------------------------
    # AgentProvider interface
    # ------------------------------------------------------------------

    def complete(self, system_prompt: str, user_prompt: str) -> CompletionResult:
        """Call the OpenAI chat completions endpoint."""
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as error:
            if getattr(error, "status_code", None) == 404 and "DeploymentNotFound" in str(error):
                raise RuntimeError(
                    f"Foundry deployment {self._model!r} was not found. "
                    "Set FOUNDRY_MODEL to the exact deployment name shown in "
                    "Microsoft Foundry, not the underlying model name."
                ) from error
            raise

        content = response.choices[0].message.content or ""
        return CompletionResult(
            content=content,
            raw=response.model_dump(),
        )
        
    def chat_with_tools(
        self,
        messages: list[AgentMessage],
        tools: list[ToolDefinition] | None = None,
        tool_choice: str | dict = "auto",
    ) -> AgentMessage:
        openai_messages = []
        for msg in messages:
            m = {"role": msg.role}
            if msg.content is not None:
                m["content"] = msg.content
            if msg.tool_call_id is not None:
                m["tool_call_id"] = msg.tool_call_id
            if msg.tool_calls:
                m["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    } for tc in msg.tool_calls
                ]
            openai_messages.append(m)

        kwargs = {
            "model": self._model,
            "messages": openai_messages,
        }
        
        if tools:
            kwargs["tools"] = [t.to_openai_schema() for t in tools]
            kwargs["tool_choice"] = tool_choice

        response = self._client.chat.completions.create(**kwargs)
        resp_msg = response.choices[0].message
        
        parsed_tool_calls = None
        if resp_msg.tool_calls:
            parsed_tool_calls = []
            for tc in resp_msg.tool_calls:
                parsed_tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments)
                ))
                
        return AgentMessage(
            role=resp_msg.role,
            content=resp_msg.content,
            tool_calls=parsed_tool_calls,
        )

    # complete_from_template() uses the default base-class implementation,
    # which parses the YAML, substitutes {steps[0].input.field}, and
    # delegates to complete().
