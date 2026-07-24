"""Ollama local agent provider."""

import json
import urllib.request
from config import config
from agents.base import AgentProvider, CompletionResult


class OllamaAgent(AgentProvider):
    """AgentProvider backed by a local Ollama instance."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self._base_url = (base_url or config.OLLAMA_BASE_URL).rstrip("/")
        self._model = model or config.OLLAMA_MODEL

    def complete(self, system_prompt: str, user_prompt: str) -> CompletionResult:
        """Call local Ollama /api/chat endpoint."""
        url = f"{self._base_url}/api/chat"
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req) as resp:
                result_data = json.loads(resp.read().decode("utf-8"))
                content = result_data.get("message", {}).get("content", "")
                return CompletionResult(content=content, raw=result_data)
        except Exception as error:
            raise RuntimeError(
                f"Failed to connect to local Ollama at {url}. "
                f"Ensure Ollama is running ('ollama serve') and model {self._model!r} is pulled ('ollama pull {self._model}')."
            ) from error
