"""
Article Embedding Pipeline Stage.

Generates vector embeddings for processed news articles and saves them
into each article's JSON file so the RAG Chatbot can perform semantic retrieval.
"""

from service.db import FileStore
from config import config
from pipeline.embeddings.factory import create_embedding_provider
from service.logger import log


def generate_embeddings(progress_callback=None, provider_name=None):
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

    processed_files = FileStore.list_processed_files()
    if not processed_files:
        log.warn("No processed articles found to embed.")
        return

    log.info(f"Using Embedding Provider: {target_provider}", f"{len(processed_files)} articles total")

    total = len(processed_files)
    updated_count = 0

    for idx, filepath in enumerate(processed_files, 1):
        if progress_callback:
            progress_callback(idx, total, f"Embedding {filepath.name}")

        try:
            article = FileStore.read_json(filepath)
            
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
                FileStore.write_json(filepath, article)
                updated_count += 1
                log.info(f"Embedded [{idx}/{total}]", f"{filepath.name} (dims: {len(vector)})")
        except Exception as e:
            log.error(f"Error embedding {filepath.name}", str(e))

    log.success("Embedding stage complete", f"Generated embeddings for {updated_count} articles")


if __name__ == "__main__":
    generate_embeddings()
