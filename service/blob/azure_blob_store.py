"""Azure Blob Storage implementation of ArticleStore.

Stores processed news articles as JSON blobs in an Azure Storage container.
Each article is stored as ``{article_id}.json`` in the configured container.

Requires the ``azure-storage-blob`` package and an
``AZURE_STORAGE_CONNECTION_STRING`` environment variable.
"""

import json
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

from service.blob.article_store import ArticleStore

try:
    from service.logger import log
except ImportError:
    log = None


def _json_content_settings():
    try:
        from azure.storage.blob import ContentSettings
        return ContentSettings(content_type="application/json")
    except Exception:
        return None


class AzureBlobArticleStore(ArticleStore):
    """ArticleStore backed by Azure Blob Storage with fast in-memory caching."""

    def __init__(
        self,
        connection_string: str,
        container_name: str = "processed-articles",
    ):
        if not connection_string:
            raise ValueError(
                "AZURE_STORAGE_CONNECTION_STRING is required for the 'azure' article store backend."
            )
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError as err:
            raise RuntimeError(
                "azure-storage-blob is required for the 'azure' article store backend. "
                "Install with `pip install azure-storage-blob`."
            ) from err

        self._service_client = BlobServiceClient.from_connection_string(connection_string)
        self._container_name = container_name
        self._container_client = self._service_client.get_container_client(container_name)
        self._ensure_container()
        # Fast in-memory cache for article metadata & full articles
        self._meta_cache: dict[str, dict] = {}
        self._article_cache: dict[str, dict] = {}
        self._manifest_blob_name = "manifest.json"

    def _ensure_container(self):
        """Create the blob container if it does not already exist."""
        try:
            self._container_client.get_container_properties()
        except Exception:
            try:
                self._container_client.create_container()
                if log:
                    log.db("Azure Blob", f"Created container '{self._container_name}'")
            except Exception as e:
                if log:
                    log.warn("Azure Blob container creation failed", str(e))

    def _blob_name(self, article_id: str) -> str:
        return f"{article_id}.json"

    # --- ArticleStore Interface ---

    def article_exists(
        self, title_or_id: str, pub_date: str | int | float | None = None
    ) -> bool:
        if pub_date is not None:
            article_id = self.compute_article_id(title_or_id, pub_date)
        else:
            article_id = title_or_id

        if article_id in self._meta_cache or article_id in self._article_cache:
            return True

        blob_client = self._container_client.get_blob_client(self._blob_name(article_id))
        try:
            blob_client.get_blob_properties()
            return True
        except Exception:
            return False

    def save_article(self, article_data: dict, article_id: str | None = None) -> str:
        if not article_id:
            article_id = self.compute_article_id(
                article_data.get("title", ""), article_data.get("publication_date", "")
            )
        self._ensure_created_at(article_data)

        blob_client = self._container_client.get_blob_client(self._blob_name(article_id))
        json_bytes = json.dumps(article_data, indent=2, ensure_ascii=False).encode("utf-8")

        # Encode metadata headers so list_articles() can fetch metadata in 1 single HTTP request
        title = str(article_data.get("title", "Untitled"))[:200].encode("ascii", "ignore").decode("ascii")
        category = str(article_data.get("category", ""))[:50].encode("ascii", "ignore").decode("ascii")
        pub_date = str(article_data.get("publication_date", ""))[:30].encode("ascii", "ignore").decode("ascii")

        src = article_data.get("source") or {}
        source_str = ""
        if isinstance(src, dict):
            source_str = src.get("name") or src.get("title") or src.get("subreddit") or ""
        elif isinstance(src, str):
            source_str = src

        metadata = {
            "title": title or "Untitled",
            "category": category,
            "publication_date": pub_date,
            "source": str(source_str)[:100].encode("ascii", "ignore").decode("ascii"),
        }

        settings = _json_content_settings()
        if settings:
            blob_client.upload_blob(
                json_bytes,
                overwrite=True,
                metadata=metadata,
                content_settings=settings,
            )
        else:
            blob_client.upload_blob(
                json_bytes,
                overwrite=True,
                metadata=metadata,
            )

        # Cache locally
        meta_entry = {
            "id": article_id,
            "title": article_data.get("title", "Untitled"),
            "category": article_data.get("category", ""),
            "publication_date": article_data.get("publication_date", ""),
            "source": source_str,
        }
        self._meta_cache[article_id] = meta_entry
        article_copy = dict(article_data)
        article_copy["id"] = article_id
        self._article_cache[article_id] = article_copy

    def _load_manifest(self) -> list[dict] | None:
        """Fetch index manifest in 1 single HTTP request to avoid scanning thousands of individual blobs."""
        try:
            blob_client = self._container_client.get_blob_client(self._manifest_blob_name)
            data = blob_client.download_blob().readall()
            items = json.loads(data.decode("utf-8"))
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and "id" in item:
                        self._meta_cache[item["id"]] = item
                return items
        except Exception:
            pass
        return None

    def _sync_manifest(self):
        """Update manifest.json index blob in Azure Container."""
        try:
            items = list(self._meta_cache.values())
            json_bytes = json.dumps(items, ensure_ascii=False).encode("utf-8")
            blob_client = self._container_client.get_blob_client(self._manifest_blob_name)
            settings = _json_content_settings()
            if settings:
                blob_client.upload_blob(json_bytes, overwrite=True, content_settings=settings)
            else:
                blob_client.upload_blob(json_bytes, overwrite=True)
        except Exception as e:
            if log:
                log.warn("Azure manifest sync failed", str(e))

    def save_articles_batch(self, articles_data: list[dict], max_workers: int = 15) -> list[str]:
        """Fast multi-threaded concurrent upload of a batch of articles to Azure Blob Storage."""
        if not articles_data:
            return []

        ids = []
        def _upload_single(art: dict) -> str:
            return self.save_article(art)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_upload_single, art) for art in articles_data if isinstance(art, dict)]
            for future in as_completed(futures):
                try:
                    aid = future.result()
                    if aid:
                        ids.append(aid)
                except Exception as e:
                    if log:
                        log.error("Azure batch upload error", str(e))

        # Sync updated manifest index blob
        self._sync_manifest()
        return ids

    def load_article(self, article_id: str) -> dict | None:
        if article_id in self._article_cache:
            return dict(self._article_cache[article_id])

        blob_client = self._container_client.get_blob_client(self._blob_name(article_id))
        try:
            data = blob_client.download_blob().readall()
            article = json.loads(data.decode("utf-8"))
            if isinstance(article, dict):
                article["id"] = article_id
                self._article_cache[article_id] = article
                src = article.get("source") or {}
                source_str = ""
                if isinstance(src, dict):
                    source_str = src.get("name") or src.get("title") or src.get("subreddit") or ""
                elif isinstance(src, str):
                    source_str = src
                self._meta_cache[article_id] = {
                    "id": article_id,
                    "title": article.get("title", "Untitled"),
                    "category": article.get("category", ""),
                    "publication_date": article.get("publication_date", ""),
                    "source": source_str,
                }
            return article
        except Exception:
            return None

    def list_articles(self, limit: int | None = None) -> list[dict]:
        """Return article metadata using 1-request manifest index, fallback to parallel scanning."""
        # 1. Check local cache or manifest.json index blob (1 HTTP GET call!)
        if not self._meta_cache:
            self._load_manifest()

        if self._meta_cache:
            results = list(self._meta_cache.values())
            if limit and limit > 0:
                return results[:limit]
            return results

        # 2. Fallback: Scan container blobs if manifest does not exist yet
        results = []
        try:
            blobs = [
                b for b in self._container_client.list_blobs(include="metadata")
                if b.name.endswith(".json") and b.name != self._manifest_blob_name
            ]
            if limit and limit > 0:
                blobs = blobs[:limit]

            uncached_ids = []
            for blob in blobs:
                article_id = blob.name.removesuffix(".json")
                meta = blob.metadata or {}
                title = meta.get("title")

                if article_id in self._meta_cache:
                    results.append(self._meta_cache[article_id])
                elif title and title != article_id:
                    meta_entry = {
                        "id": article_id,
                        "title": title,
                        "category": meta.get("category", ""),
                        "publication_date": meta.get("publication_date", ""),
                        "source": meta.get("source", ""),
                    }
                    self._meta_cache[article_id] = meta_entry
                    results.append(meta_entry)
                else:
                    uncached_ids.append(article_id)

            if uncached_ids:
                def _fetch_one(aid: str) -> dict | None:
                    return self.load_article(aid)

                with ThreadPoolExecutor(max_workers=30) as executor:
                    futures = [executor.submit(_fetch_one, aid) for aid in uncached_ids]
                    for future in as_completed(futures):
                        art = future.result()
                        if art and art.get("id") in self._meta_cache:
                            results.append(self._meta_cache[art["id"]])

            # Save manifest index for fast 1-request retrieval on subsequent calls
            self._sync_manifest()
        except Exception as e:
            if log:
                log.error("Azure list_articles error", str(e))
        return results

    def load_all_articles(self, limit: int | None = None) -> list[dict]:
        """Load full content of articles in parallel with local cache support and optional limits."""
        articles = []
        try:
            blob_names = [
                b.name for b in self._container_client.list_blobs()
                if b.name.endswith(".json") and b.name != self._manifest_blob_name
            ]
            if limit and limit > 0:
                blob_names = blob_names[:limit]

            uncached_ids = []
            for name in blob_names:
                article_id = name.removesuffix(".json")
                if article_id in self._article_cache:
                    articles.append(dict(self._article_cache[article_id]))
                else:
                    uncached_ids.append(article_id)

            if uncached_ids:
                def _fetch_one(aid: str) -> dict | None:
                    return self.load_article(aid)

                with ThreadPoolExecutor(max_workers=30) as executor:
                    futures = [executor.submit(_fetch_one, aid) for aid in uncached_ids]
                    for future in as_completed(futures):
                        res = future.result()
                        if res:
                            articles.append(res)
        except Exception as e:
            if log:
                log.error("Azure load_all_articles error", str(e))
        return articles
