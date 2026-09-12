"""
Modern Prompt management for DistillNews.

Loads and renders .prompt.md templates with structured System/User sections,
YAML frontmatter metadata, and case-insensitive placeholder substitution.
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import Any
import yaml


class Prompt:
    """Represents a structured prompt template.

    Basic usage:
        prompt = Prompt("pipeline/prompts/news_from_html.prompt.md")
        rendered = prompt.fill(NEWS="Some news article...")

        # Access system and user components
        system_text = rendered.system
        user_text = rendered.user

        # String coercion
        print(str(rendered))
    """

    def __init__(
        self,
        source: str | Path,
        is_content: bool = False,
        system: str | None = None,
        user: str | None = None,
        metadata: dict | None = None,
    ):
        self.metadata: dict = metadata or {}
        self.system: str = system or ""
        self.user: str = user or ""
        self.raw_content: str = ""
        self._source_path: Path | None = None

        if system is None and user is None:
            if is_content:
                self.raw_content = str(source)
            else:
                path = Path(source)
                self._source_path = path
                with open(path, "r", encoding="utf-8") as f:
                    self.raw_content = f.read()
            self._parse(self.raw_content)

    def _parse(self, content: str) -> None:
        """Parse frontmatter and split # System and # User sections."""
        # Optional YAML frontmatter delimited by ---
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", content, re.DOTALL)
        if fm_match:
            fm_text, body = fm_match.group(1), fm_match.group(2)
            try:
                loaded = yaml.safe_load(fm_text)
                if isinstance(loaded, dict):
                    self.metadata = loaded
            except Exception:
                self.metadata = {}
        else:
            body = content

        # Split # System and # User sections (markdown headings)
        sys_pattern = r"(?:^|\n)#+\s*System\s*\n"
        user_pattern = r"(?:^|\n)#+\s*User\s*\n"

        sys_split = re.split(sys_pattern, body, maxsplit=1, flags=re.IGNORECASE)
        if len(sys_split) > 1:
            after_sys = sys_split[1]
            user_split = re.split(user_pattern, after_sys, maxsplit=1, flags=re.IGNORECASE)
            if len(user_split) > 1:
                self.system = user_split[0].strip()
                self.user = user_split[1].strip()
            else:
                self.system = after_sys.strip()
                self.user = ""
        else:
            user_split = re.split(user_pattern, body, maxsplit=1, flags=re.IGNORECASE)
            if len(user_split) > 1:
                self.system = user_split[0].strip()
                self.user = user_split[1].strip()
            else:
                self.system = ""
                self.user = body.strip()

    @staticmethod
    def _format_news_dict(data: dict) -> str:
        """Format a dictionary into a clean News representation block."""
        parts = []
        if data.get("title"):
            parts.append(f"Title: {data['title']}")
        if data.get("author"):
            parts.append(f"Author: {data['author']}")
        if data.get("publication_date"):
            parts.append(f"Published: {data['publication_date']}")
        if data.get("content"):
            parts.append(f"Content:\n{data['content']}")
        elif data.get("text"):
            parts.append(f"Content:\n{data['text']}")
        elif not parts:
            return "\n\n".join(f"{k}: {v}" for k, v in data.items())
        return "\n\n".join(parts)

    def fill(self, **kwargs: Any) -> "Prompt":
        """Substitute {{KEY}} placeholders using case-insensitive keyword mapping.

        Supports:
        - Passing `news="..."` or `NEWS="..."`
        - Passing a dictionary `news={"title": ..., "content": ...}` (auto-formats into {{NEWS}})
        - Synthesizing `news` when `title` and `content` are provided as keyword arguments
        - Explicit keyword arguments matching {{TITLE}}, {{CONTENT}}, etc.
        - Legacy `{steps[0].input.field}` syntax for backward compatibility.
        """
        lower_kwargs: dict[str, Any] = {}
        for k, v in kwargs.items():
            lower_kwargs[k.lower()] = v

        # If 'news' is given as a dict, format it and also unpack its keys
        news_val = lower_kwargs.get("news")
        if isinstance(news_val, dict):
            for nk, nv in news_val.items():
                if nk.lower() not in lower_kwargs:
                    lower_kwargs[nk.lower()] = nv
            lower_kwargs["news"] = self._format_news_dict(news_val)
        elif news_val is None:
            # If 'news' key is not provided directly, synthesize it from title/content
            if "title" in lower_kwargs or "content" in lower_kwargs:
                synthesized = []
                if lower_kwargs.get("title"):
                    synthesized.append(f"Title: {lower_kwargs['title']}")
                if lower_kwargs.get("author"):
                    synthesized.append(f"Author: {lower_kwargs['author']}")
                if lower_kwargs.get("publication_date"):
                    synthesized.append(f"Published: {lower_kwargs['publication_date']}")
                if lower_kwargs.get("content"):
                    synthesized.append(f"Content:\n{lower_kwargs['content']}")
                lower_kwargs["news"] = "\n\n".join(synthesized)

        def _substitute(text: str) -> str:
            def _replacer(match: re.Match) -> str:
                raw_key = match.group(1) or match.group(2) or ""
                key = raw_key.strip().lower()
                if key in lower_kwargs:
                    val = lower_kwargs[key]
                    return str(val) if val is not None else ""
                return match.group(0)

            # Match {{ KEY }} or {steps[0].input.KEY}
            pattern = r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}|\{steps\[0\]\.input\.(\w+)\}"
            return re.sub(pattern, _replacer, text)

        new_sys = _substitute(self.system)
        new_usr = _substitute(self.user)

        return Prompt(
            source=self._source_path or "",
            is_content=True,
            system=new_sys,
            user=new_usr,
            metadata=dict(self.metadata),
        )

    def __str__(self) -> str:
        if self.system and self.user:
            return f"{self.system}\n\n{self.user}"
        return self.user or self.system

    def __repr__(self) -> str:
        name = self.metadata.get("name", self._source_path.name if self._source_path else "InlinePrompt")
        return f"<Prompt name={name!r} has_system={bool(self.system)} has_user={bool(self.user)}>"
