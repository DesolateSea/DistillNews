"""
OpenAI agent provider.

Uses the OpenAI Python SDK for chat completions.
Also works with OpenAI-compatible APIs (Azure OpenAI, Grok, local servers)
by setting ``OPENAI_BASE_URL``.
"""

import os

from dotenv import load_dotenv

from agents.base import AgentProvider, CompletionResult

load_dotenv()


class OpenAIAgent(AgentProvider):
    """AgentProvider backed by the OpenAI chat completions API.

    Constructor args can override env-var defaults:
        - ``api_key``  → ``OPENAI_API_KEY``
        - ``model``    → ``AGENT_MODEL``
        - ``base_url`` → ``OPENAI_BASE_URL`` (for Azure / Grok / local)
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ):
        from openai import OpenAI  # defer import so the SDK is optional

        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._model = model or os.getenv("AGENT_MODEL", "gpt-4o-mini")
        self._base_url = base_url or os.getenv("OPENAI_BASE_URL")

        client_kwargs: dict = {"api_key": self._api_key}
        if self._base_url:
            client_kwargs["base_url"] = self._base_url

        self._client = OpenAI(**client_kwargs)

    # ------------------------------------------------------------------
    # AgentProvider interface
    # ------------------------------------------------------------------

    def complete(self, system_prompt: str, user_prompt: str) -> CompletionResult:
        """Call the OpenAI chat completions endpoint."""
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content or ""
        return CompletionResult(
            content=content,
            raw=response.model_dump(),
        )

    # complete_from_template() uses the default base-class implementation,
    # which parses the YAML, substitutes {steps[0].input.field}, and
    # delegates to complete().
