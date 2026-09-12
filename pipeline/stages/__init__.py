"""
Pipeline stages — modular @stage-decorated functions.

Importing this package registers all producer and transform stages
with the global stage registry.
"""

# Producer stages (sources)
from pipeline.stages.sources import (  # noqa: F401
    reddit,
    gnews,
    scrape,
    rapid_news,
    media_stack,
    news_org,
    core,
)

# Transform stages
from pipeline.stages import (  # noqa: F401
    parse as _parse,
    dedup as _dedup,
    classify as _classify,
    extract as _extract,
    format as _format,
    embed as _embed,
    persist as _persist,
)
