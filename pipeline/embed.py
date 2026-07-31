import math
from service.db import FileStore, create_article_store
from config import config
from pipeline.embeddings.factory import create_embedding_provider
from service.logger import log


def _normalize_vector(vec: list[float]) -> list[float]:
    if not vec:
        return []
    sq_sum = sum(x * x for x in vec)
    if sq_sum == 0:
        return vec
    norm = math.sqrt(sq_sum)
    return [x / norm for x in vec]


def generate_embeddings(progress_callback=None, provider_name=None, stop_checker=None, force: bool = False):
    """
    Generate pre-normalized vector embeddings in 32-article batches for all processed articles.
    If force=True, re-generates and overwrites embeddings in-place in storage without creating duplicate copies.
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

    log.info(f"Using Embedding Provider: {target_provider}", f"{len(articles)} articles total (force={force})")

    queued_articles = []
    for article in articles:
        has_emb = article.get("embedding") and isinstance(article["embedding"], list) and len(article["embedding"]) > 0
        if force or not has_emb:
            title = article.get("title", "")
            content = article.get("content") or article.get("markdown_content") or article.get("summary") or ""
            text_to_embed = f"{title}\n\n{content}".strip()
            if text_to_embed:
                queued_articles.append((article, text_to_embed))

    total = len(queued_articles)
    if total == 0:
        log.success("Embedding stage complete", "All articles already have pre-normalized vector embeddings")
        return

    log.info("Starting batched embedding generation", f"{total} unembedded articles queued")

    batch_size = 32
    updated_count = 0

    for i in range(0, total, batch_size):
        if stop_checker and stop_checker():
            log.warn("Cancellation requested", "Stopping embedding stage immediately")
            break

        batch = queued_articles[i : i + batch_size]
        batch_texts = [text for _, text in batch]

        if progress_callback:
            progress_callback(min(i + len(batch), total), total, f"Embedding batch {i // batch_size + 1}")

        try:
            vectors = provider.embed_many(batch_texts)
            for (article, _), vector in zip(batch, vectors):
                if vector:
                    norm_vec = _normalize_vector(vector)
                    article["embedding"] = norm_vec
                    article_store.save_article(article, article_id=article.get('id'))
                    updated_count += 1
            log.info(f"Embedded batch [{min(i + len(batch), total)}/{total}]", f"{len(vectors)} vectors generated & L2-normalized")
        except Exception as e:
            log.error(f"Error embedding batch starting at index {i}", str(e))

    log.success("Embedding stage complete", f"Generated & pre-normalized embeddings for {updated_count} articles")


if __name__ == "__main__":
    generate_embeddings()
