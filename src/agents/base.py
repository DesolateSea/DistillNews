"""
Abstract base class for all LLM agent providers.

This interface covers ONLY text completion / chat.
RAG (document storage & search) is a separate concern — see rag.base.
"""

import re
import yaml
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CompletionResult:
    """Standard result from any agent provider."""

    content: str  # The text response
    raw: dict | None = field(default=None, repr=False)  # Provider-specific raw response


class AgentProvider(ABC):
    """Abstract base for LLM completion backends.

    Subclasses must implement ``complete()``.
    ``complete_from_template()`` has a default implementation that parses
    YAML prompt files and delegates to ``complete()``; providers with native
    task/template support (e.g., Julep) can override it.
    """

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> CompletionResult:
        """Send a system + user prompt pair and return the text response."""

    # ------------------------------------------------------------------
    # Template helpers
    # ------------------------------------------------------------------

    def complete_from_template(
        self, template_path: str | Path, input_data: dict
    ) -> CompletionResult:
        """Load a YAML prompt template, substitute variables, call ``complete()``.

        The default implementation:
        1. Reads the YAML file.
        2. Extracts the system and user message content.
        3. Replaces ``{steps[0].input.<key>}`` with the corresponding
           value from *input_data*.
        4. Delegates to ``self.complete()``.

        Providers with native template execution (Julep) should override this.
        """
        system_prompt, user_prompt = self._render_template(template_path, input_data)
        return self.complete(system_prompt, user_prompt)

    # ------------------------------------------------------------------

    @staticmethod
    def _render_template(
        template_path: str | Path, input_data: dict
    ) -> tuple[str, str]:
        """Parse a YAML prompt file and substitute Julep-style variables.

        Handles the ``{steps[0].input.field}`` syntax used in the existing
        YAML templates by mapping them to keys in *input_data*.

        Returns:
            (system_prompt, user_prompt)
        """
        with open(template_path, "r", encoding="utf-8") as f:
            task_def = yaml.safe_load(f)

        # The YAML structure is:
        #   main:
        #     - prompt:
        #         - { role: system, content: "..." }
        #         - { role: user,   content: "..." }
        main = task_def.get("main", [])
        if not main:
            raise ValueError(f"No 'main' key in template: {template_path}")

        # 'prompt' can be a direct key or nested under the first main entry
        prompt_messages = main[0].get("prompt", [])

        system_content = ""
        user_content = ""
        for msg in prompt_messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                system_content = content
            elif role == "user":
                user_content = content

        def _substitute(text: str) -> str:
            """Replace {steps[0].input.field} with input_data['field']."""
            def _replacer(match: re.Match) -> str:
                key = match.group(1)
                value = input_data.get(key, "")
                return str(value) if value is not None else ""

            return re.sub(r"\{steps\[0\]\.input\.(\w+)\}", _replacer, text)

        return _substitute(system_content), _substitute(user_content)
