import os
from mcp.server.fastmcp import FastMCP

default_host = os.environ.get("FASTMCP_HOST", "0.0.0.0")
default_port = int(os.environ.get("MCP_PORT") or os.environ.get("FASTMCP_PORT", "8002"))

mcp = FastMCP("DistillNews Engine", host=default_host, port=default_port)

# Wrap run() for backwards-compatibility with port/host kwargs
_orig_run = mcp.run


def _run(transport: str = "stdio", mount_path: str | None = None, **kwargs):
    if "port" in kwargs:
        mcp.settings.port = int(kwargs.pop("port"))
    if "host" in kwargs:
        mcp.settings.host = str(kwargs.pop("host"))
    return _orig_run(transport=transport, mount_path=mount_path, **kwargs)


mcp.run = _run

@mcp.tool()
def news_search(query: str, limit: int = 5, category: str | None = None) -> list[dict]:
    """Search the DistillNews corpus for relevant news articles using vector similarity and keyword matching."""
    from mcp_server.tools.search import search_news
    return search_news(query=query, limit=limit, category=category)

@mcp.tool()
def get_article(article_id: str) -> dict:
    """Retrieve the full content and metadata of a specific article by its ID."""
    from mcp_server.tools.articles import fetch_article
    return fetch_article(article_id=article_id)

@mcp.tool()
def list_categories() -> list[str]:
    """List all available news categories in the corpus."""
    return ["World", "Business", "Technology", "Entertainment", "Sports", "Science", "Health"]

@mcp.tool()
def get_article_count() -> dict:
    """Get the total number of articles in the corpus."""
    from mcp_server.tools.articles import count_articles
    return count_articles()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="DistillNews MCP Server")
    parser.add_argument(
        "--transport",
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
        choices=["stdio", "sse", "streamable-http"],
        help="MCP transport protocol (stdio, sse, streamable-http)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("FASTMCP_HOST", default_host),
        help="Host to bind for SSE/HTTP",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_PORT") or os.environ.get("FASTMCP_PORT", default_port)),
        help="Port to bind for SSE/HTTP",
    )
    args, _ = parser.parse_known_args()

    mcp.settings.host = args.host
    mcp.settings.port = args.port
    mcp.run(transport=args.transport)

if __name__ == "__main__":
    main()
