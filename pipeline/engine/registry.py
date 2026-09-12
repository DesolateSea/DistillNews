"""
Stage registry — collects stage definitions, validates the DAG, and
provides topological ordering + Mermaid export.

Usage::

    registry = StageRegistry()
    registry.discover()                 # pick up all @stage-decorated funcs
    registry.add(my_custom_stage_def)   # or add manually
    order = registry.topological_order()
    print(registry.export_mermaid())
"""

from __future__ import annotations

from collections import deque
from typing import Iterator

from pipeline.engine.stage import StageDefinition, get_registered_stages


class CyclicDependencyError(Exception):
    """Raised when the stage DAG contains a cycle."""
    pass


class MissingStageDependencyError(Exception):
    """Raised when a stage depends on an unregistered stage."""
    pass


class StageRegistry:
    """
    A validated, immutable-after-build collection of ``StageDefinition``
    objects that form a DAG.
    """

    def __init__(self) -> None:
        self._stages: dict[str, StageDefinition] = {}

    # ── population ──────────────────────────────────────────────────

    def add(self, defn: StageDefinition | Any) -> None:
        """Register a single stage definition (or a @stage-decorated callable)."""
        if hasattr(defn, "__stage__"):
            defn = getattr(defn, "__stage__")
        self._stages[defn.name] = defn

    def discover(self) -> None:
        """
        Import all globally-registered ``@stage`` functions.
        Call this *after* importing every module that contains stages.
        """
        for defn in get_registered_stages():
            self.add(defn)

    # ── queries ─────────────────────────────────────────────────────

    def __contains__(self, name: str) -> bool:
        return name in self._stages

    def __getitem__(self, name: str) -> StageDefinition:
        return self._stages[name]

    def __len__(self) -> int:
        return len(self._stages)

    def __iter__(self) -> Iterator[StageDefinition]:
        return iter(self._stages.values())

    @property
    def names(self) -> list[str]:
        return list(self._stages.keys())

    @property
    def producers(self) -> list[StageDefinition]:
        """Return all producer stages (entry points of the DAG)."""
        return [s for s in self._stages.values() if s.is_producer]

    @property
    def transforms(self) -> list[StageDefinition]:
        """Return all transform stages."""
        return [s for s in self._stages.values() if not s.is_producer]

    # ── validation ──────────────────────────────────────────────────

    def validate(self) -> None:
        """
        Check for missing dependencies and cycles.
        Raises ``MissingStageDependencyError`` or ``CyclicDependencyError``.
        """
        # 1. Check all deps exist
        for defn in self._stages.values():
            for dep in defn.dependencies:
                if dep not in self._stages:
                    raise MissingStageDependencyError(
                        f"Stage {defn.name!r} depends on {dep!r}, "
                        f"which is not registered. "
                        f"Known stages: {sorted(self._stages.keys())}"
                    )

        # 2. Check for cycles via Kahn's algorithm (in-degree method)
        in_degree: dict[str, int] = {name: 0 for name in self._stages}
        for defn in self._stages.values():
            for dep in defn.dependencies:
                in_degree[defn.name] += 1  # defn depends on dep → edge dep→defn

        queue: deque[str] = deque(
            name for name, deg in in_degree.items() if deg == 0
        )
        visited = 0
        while queue:
            node = queue.popleft()
            visited += 1
            # find stages that depend on `node`
            for defn in self._stages.values():
                if node in defn.dependencies:
                    in_degree[defn.name] -= 1
                    if in_degree[defn.name] == 0:
                        queue.append(defn.name)

        if visited != len(self._stages):
            remaining = [n for n, d in in_degree.items() if d > 0]
            raise CyclicDependencyError(
                f"Cycle detected among stages: {remaining}"
            )

    # ── topological ordering ────────────────────────────────────────

    def topological_order(self) -> list[str]:
        """
        Return stage names in a valid execution order (Kahn's algorithm).
        Calls ``validate()`` first to ensure the DAG is well-formed.
        """
        self.validate()

        in_degree: dict[str, int] = {name: 0 for name in self._stages}
        # adjacency: dep → list of stages that depend on it
        adjacency: dict[str, list[str]] = {name: [] for name in self._stages}

        for defn in self._stages.values():
            for dep in defn.dependencies:
                in_degree[defn.name] += 1
                adjacency[dep].append(defn.name)

        queue: deque[str] = deque(
            sorted(name for name, deg in in_degree.items() if deg == 0)
        )
        order: list[str] = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for child in sorted(adjacency[node]):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        return order

    # ── visualisation ───────────────────────────────────────────────

    def export_mermaid(self) -> str:
        """
        Generate a Mermaid flowchart string of the stage DAG.

        Producer stages render as stadium shapes (``([name])``),
        transform stages as rounded rectangles (``(name)``).
        """
        lines = ["graph LR"]

        for defn in self._stages.values():
            if defn.is_producer:
                lines.append(f'    {defn.name}(["{defn.name} ⚡"])')
            else:
                lines.append(f'    {defn.name}("{defn.name}")')

        for defn in self._stages.values():
            for dep in defn.dependencies:
                lines.append(f"    {dep} --> {defn.name}")
            for param, stream_type in getattr(defn, "stream_dependencies", ()):
                stream_label = getattr(stream_type, "__name__", str(stream_type))
                lines.append(f"    stream_{stream_label}[[\"Stream: {stream_label}\"]] --> {defn.name}")

        return "\n".join(lines)
