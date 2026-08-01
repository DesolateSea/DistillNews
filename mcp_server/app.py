from mcp.server.fastmcp import FastMCP

mcp = FastMCP("DistillNews Engine")

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
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
