"""
Article Embedding Pipeline Stage.

Generates vector embeddings for processed news articles and saves them
into each article's JSON file so the RAG Chatbot can perform semantic retrieval.
"""

from service.db import FileStore, create_article_store
from config import config
from pipeline.embeddings.factory import create_embedding_provider
from service.logger import log


def generate_embeddings(progress_callback=None, provider_name=None, stop_checker=None):
    """
    Generate vector embeddings for all processed articles that do not have them yet.
    """
    log.section("Article Embedding Pipeline Stage")

    target_provider = provider_name or config.EMBEDDING_PROVIDER
    if target_provider.lower() == "none":
        target_provider = "sentence_transformers"

    try:
        provider = create_embedding_provider(provider=target_provider)
    except Exception as e:
        log.error("Failed to initialize embedding provider", str(e))
        return

    article_store = create_article_store()
    articles = list(article_store.load_all_articles())
    if not articles:
        log.warn("No processed articles found to embed.")
        return

    log.info(f"Using Embedding Provider: {target_provider}", f"{len(articles)} articles total")

    total = len(articles)
    updated_count = 0

    for idx, article in enumerate(articles, 1):
        if stop_checker and stop_checker():
            log.warn("Cancellation requested", "Stopping embedding stage immediately")
            break

        article_id = article.get('id', 'unknown')

        if progress_callback:
            progress_callback(idx, total, f"Embedding {article_id[:16]}")

        try:
            
            # Skip if embedding vector already exists and is non-empty
            if article.get("embedding") and isinstance(article["embedding"], list) and len(article["embedding"]) > 0:
                continue

            title = article.get("title", "")
            content = article.get("content") or article.get("markdown_content") or article.get("summary") or ""
            text_to_embed = f"{title}\n\n{content}".strip()

            if not text_to_embed:
                continue

            vector = provider.embed(text_to_embed)
            if vector:
                article["embedding"] = vector
                article_store.save_article(article, article_id=article.get('id'))
                updated_count += 1
                log.info(f"Embedded [{idx}/{total}]", f"{article_id[:16]} (dims: {len(vector)})")
        except Exception as e:
            log.error(f"Error embedding {article_id[:16]}", str(e))

    log.success("Embedding stage complete", f"Generated embeddings for {updated_count} articles")


if __name__ == "__main__":
    generate_embeddings()
