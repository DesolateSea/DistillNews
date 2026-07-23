"""HuggingFace agent provider."""

import json
import urllib.request
from config import config
from agents.base import AgentProvider, CompletionResult


class HuggingFaceAgent(AgentProvider):
    """AgentProvider backed by HuggingFace Inference API or local model endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self._api_key = api_key or config.HUGGINGFACE_API_KEY
        self._model = model or config.HUGGINGFACE_MODEL

    def complete(self, system_prompt: str, user_prompt: str) -> CompletionResult:
        """Call HuggingFace Chat Completions endpoint."""
        url = f"https://api-inference.huggingface.co/models/{self._model}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 1024,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req) as resp:
                result_data = json.loads(resp.read().decode("utf-8"))
                content = result_data["choices"][0]["message"]["content"]
                return CompletionResult(content=content, raw=result_data)
        except Exception as error:
            raise RuntimeError(
                f"HuggingFace inference failed for model {self._model!r}: {error}"
            ) from error
