"""
Streaming task-graph pipeline engine.

Core primitives for defining, registering, and executing pipeline stages
as a DAG of per-article tasks with automatic dependency injection and stream channels.
"""

from pipeline.engine.task import (
    TaskState,
    TaskEvent,
    Task,
    DropArticle,
    PipelineContext,
)
from pipeline.engine.stage import stage, StageDefinition
from pipeline.engine.registry import StageRegistry
from pipeline.engine.runner import StreamingRunner
from pipeline.engine.stream import (
    Stream,
    QueueStream,
    StreamItem,
    RawArticle,
    is_stream_type,
)

__all__ = [
    "stage",
    "StageDefinition",
    "StageRegistry",
    "StreamingRunner",
    "TaskState",
    "TaskEvent",
    "Task",
    "DropArticle",
    "PipelineContext",
    "Stream",
    "QueueStream",
    "StreamItem",
    "RawArticle",
    "is_stream_type",
]
