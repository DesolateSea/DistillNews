"""
Julep agent provider.

Wraps the Julep SDK behind the abstract AgentProvider interface.
Supports both simple completions and native Julep task execution
(agents → tasks → executions with polling).
"""

import os
import time
import yaml
from pathlib import Path
from functools import lru_cache

from config import config
from service.agents.base import AgentProvider, CompletionResult


class JulepAgent(AgentProvider):
    """AgentProvider backed by the Julep AI platform.

    Constructor args can override env-var defaults:
        - ``api_key``  → ``JULEP_API_KEY``
        - ``model``    → ``AGENT_MODEL`` / ``JULEP_MODEL``
        - ``environment`` → ``JULEP_ENVIRONMENT``
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        environment: str | None = None,
    ):
        from julep import Julep  # defer import so the SDK is optional

        self._api_key = api_key or config.JULEP_API_KEY
        self._model = model or config.JULEP_MODEL
        self._environment = environment or config.JULEP_ENVIRONMENT

        self._client = Julep(
            api_key=self._api_key,
            environment=self._environment,
        )

    # ------------------------------------------------------------------
    # AgentProvider interface
    # ------------------------------------------------------------------

    def complete(self, system_prompt: str, user_prompt: str) -> CompletionResult:
        """Create a one-shot Julep agent + inline task, execute and poll."""
        agent = self._client.agents.create(
            name="OneShot",
            model=self._model,
            about="Temporary agent for a single completion.",
        )

        task_def = {
            "name": "inline_completion",
            "description": "Single-turn completion task.",
            "main": [
                {
                    "prompt": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ]
                }
            ],
        }
        task = self._client.tasks.create(agent_id=agent.id, **task_def)
        execution = self._client.executions.create(task_id=task.id, input={})

        result = self._poll_execution(execution.id)
        content = result["choices"][0]["message"]["content"]
        return CompletionResult(content=content, raw=result)

    def complete_from_template(
        self, template_path: str | Path, input_data: dict
    ) -> CompletionResult:
        """Use Julep's native task system — the YAML is passed through as-is.

        This preserves the ``{steps[0].input.field}`` syntax that Julep
        understands natively, so no variable substitution is needed on our side.
        """
        task = self._get_or_create_task(str(template_path))
        execution = self._client.executions.create(
            task_id=task.id, input=input_data
        )

        result = self._poll_execution(execution.id)
        content = result["choices"][0]["message"]["content"]
        return CompletionResult(content=content, raw=result)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _poll_execution(self, execution_id: str, poll_interval: float = 1.0) -> dict:
        """Poll a Julep execution until it succeeds or fails."""
        while True:
            res = self._client.executions.get(execution_id)
            if res.status == "succeeded":
                return res.output
            if res.status == "failed":
                raise RuntimeError(
                    f"Julep execution {execution_id} failed: {res}"
                )
            time.sleep(poll_interval)

    @lru_cache(maxsize=128)
    def _get_or_create_task(self, yaml_path: str) -> object:
        """Load a YAML task definition and register it with a Julep agent.

        Results are cached so repeated calls with the same path reuse
        the same agent + task.
        """
        with open(yaml_path, "r", encoding="utf-8") as f:
            task_definition = yaml.safe_load(f)

        # Derive agent name / description from the task YAML
        agent_name = task_definition.get("name", "TaskAgent")
        agent_about = task_definition.get("description", "Agent for a YAML-defined task.")

        agent = self._client.agents.create(
            name=agent_name,
            model=self._model,
            about=agent_about,
        )
        task = self._client.tasks.create(agent_id=agent.id, **task_definition)
        return task
