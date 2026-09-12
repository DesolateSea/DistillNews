"""
Stage decorator — the ``@stage`` API for defining pipeline stages.

Inspects the decorated function's signature to automatically determine:
  - stage name  (from ``function.__name__``)
  - dependencies (from parameter names matching other stage names)
  - producer vs transform (generator function → producer)

Usage::

    @stage
    def scrape_rss():
        \"\"\"Producer stage: yields raw HTML strings.\"\"\"
        for url in get_feeds():
            yield fetch(url)

    @stage
    def classify(scrape_rss: str) -> dict:
        \"\"\"Transform stage: depends on scrape_rss output.\"\"\"
        if not is_newsworthy(scrape_rss):
            raise DropArticle("spam")
        return parse(scrape_rss)

    @stage
    def extract(classify: dict, ctx: PipelineContext) -> dict:
        \"\"\"Depends on classify; also receives pipeline context.\"\"\"
        return ctx.agent.complete(classify)
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable

from pipeline.engine.stream import is_stream_type


# Names that are injected by the runner rather than resolved as
# stage-to-stage dependencies.
INJECTED_PARAMS = frozenset({"ctx"})


@dataclass(frozen=True)
class StageDefinition:
    """
    Immutable metadata extracted from a ``@stage``-decorated function.

    Attributes:
        name:                Stage name (derived from ``func.__name__``).
        func:                The original callable.
        dependencies:        Stage names this stage depends on (name-to-function matched).
        stream_dependencies: (param_name, stream_type) pairs for stream-injected parameters.
        is_producer:         True if ``func`` is a generator (uses ``yield``).
        doc:                 Docstring of the original function.
    """

    name: str
    func: Callable[..., Any]
    dependencies: tuple[str, ...]
    stream_dependencies: tuple[tuple[str, Any], ...] = ()
    is_producer: bool = False
    doc: str = ""

    def __repr__(self) -> str:
        kind = "producer" if self.is_producer else "transform"
        parts = []
        if self.dependencies:
            parts.append(f"deps=[{', '.join(self.dependencies)}]")
        if self.stream_dependencies:
            stream_names = [f"{p}:{getattr(t, '__name__', str(t))}" for p, t in self.stream_dependencies]
            parts.append(f"streams=[{', '.join(stream_names)}]")
        desc = " ".join(parts) or "∅"
        return f"<Stage {self.name!r} ({kind}) {desc}>"


# ── Global auto-registration list ──────────────────────────────────
# Stages decorated with ``@stage`` are collected here so that
# ``StageRegistry.discover()`` can pick them up.
_REGISTERED_STAGES: list[StageDefinition] = []


def get_registered_stages() -> list[StageDefinition]:
    """Return a copy of all globally registered stage definitions."""
    return list(_REGISTERED_STAGES)


def clear_registered_stages() -> None:
    """Reset the global stage list (useful in tests)."""
    _REGISTERED_STAGES.clear()


def stage(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator that registers a function as a pipeline stage.

    The decorator is transparent: it returns the original function
    unchanged, but attaches a ``__stage__`` attribute containing the
    ``StageDefinition`` and appends it to the global registry.

    Detection rules:
    - **name** = ``func.__name__``
    - **stream dependencies** = parameters annotated with a Stream or StreamItem type
    - **stage dependencies** = unannotated / standard parameters (matched to upstream function names)
    - **injected parameters** = ``ctx`` (injected pipeline context)
    - **is_producer** = ``inspect.isgeneratorfunction(func)``
    """
    sig = inspect.signature(func)

    try:
        import typing
        hints = typing.get_type_hints(func)
    except Exception:
        hints = {}

    stage_deps: list[str] = []
    stream_deps: list[tuple[str, Any]] = []

    for name, param in sig.parameters.items():
        if name in INJECTED_PARAMS:
            continue
        if param.kind not in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ):
            continue

        ann = hints.get(name, param.annotation)
        # If annotated with a Stream or StreamItem type -> Stream Injection
        if is_stream_type(ann):
            stream_deps.append((name, ann))
        else:
            # Otherwise -> Pytest name-to-function matching
            stage_deps.append(name)

    definition = StageDefinition(
        name=func.__name__,
        func=func,
        dependencies=tuple(stage_deps),
        stream_dependencies=tuple(stream_deps),
        is_producer=inspect.isgeneratorfunction(func),
        doc=(func.__doc__ or "").strip(),
    )

    # Attach metadata so downstream code can introspect without the
    # global registry.
    func.__stage__ = definition  # type: ignore[attr-defined]

    _REGISTERED_STAGES.append(definition)

    return func
