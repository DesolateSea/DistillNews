import json
from datetime import datetime, timezone
from fastapi import HTTPException
from server.models.articles_model import DurationRequest, ArticleInDB, PaginatedArticlesResponse
from server.utils.recommendation import sort_articles, get_publication_timestamp
from service.blob import ArticleStore, create_article_store
from service.db import RedisHandle

try:
    from service.logger import log
except ImportError:
    log = None

article_store: ArticleStore = create_article_store()


def _normalize_source_media(doc: dict) -> dict:
    """Preserve and normalize source.media and source.image_url as simple string URLs without stripping."""
    root_image = doc.get("image_url") or doc.get("image")
    src = doc.get("source")

    if isinstance(src, dict):
        clean_src = dict(src)
    elif isinstance(src, list) and src and isinstance(src[0], dict):
        clean_src = dict(src[0])
    elif isinstance(src, str):
        clean_src = {"title": src, "name": src}
    else:
        clean_src = {"title": "Unknown"}

    for sub_key in ("content", "markdown_content", "raw_html", "raw", "authors", "prompt_used", "raw_source_file", "agent_provider"):
        clean_src.pop(sub_key, None)

    # Extract image_url string if available
    img_url = clean_src.get("image_url") or root_image or ""
    if isinstance(img_url, list):
        img_url = img_url[0] if img_url else ""
    img_url = str(img_url).strip() if img_url else ""

    # Extract media list
    raw_media = clean_src.get("media")
    media_list: list[str] = []
    if isinstance(raw_media, list):
        for item in raw_media:
            if item and isinstance(item, (str, dict)):
                url_str = item if isinstance(item, str) else item.get("url") or item.get("src") or ""
                if url_str:
                    media_list.append(str(url_str).strip())
    elif isinstance(raw_media, str) and raw_media.strip():
        media_list.append(raw_media.strip())

    # Keep image_url and media list in sync so neither is empty if URLs exist
    if img_url and img_url not in media_list:
        media_list.insert(0, img_url)
    elif not img_url and media_list:
        img_url = media_list[0]

    clean_src["image_url"] = img_url
    clean_src["media"] = media_list

    if not clean_src.get("title") and clean_src.get("name"):
        clean_src["title"] = clean_src["name"]
    elif not clean_src.get("title"):
        clean_src["title"] = "Unknown"

    doc["source"] = clean_src
    if img_url:
        doc["image_url"] = img_url
    return doc


def _strip_heavy_fields(doc: dict) -> dict:
    """Return a clean copy of the article dict with internal/heavy fields removed for feed list views."""
    clean_doc = dict(doc)
    for heavy_key in (
        "content", "markdown_content", "summary", "embedding", "vector", "raw_html", "raw",
        "prompt_used", "raw_source_file", "agent_provider"
    ):
        clean_doc.pop(heavy_key, None)

    return _normalize_source_media(clean_doc)


def _clean_single_article(doc: dict) -> dict:
    """Return a copy of full article dict stripping internal pipeline metadata fields while retaining full text content."""
    clean_doc = dict(doc)
    for internal_key in (
        "embedding", "vector", "agent_provider", "prompt_used", "raw_source_file", "raw_html", "raw"
    ):
        clean_doc.pop(internal_key, None)

    return _normalize_source_media(clean_doc)


async def prime_redis_indexes(force: bool = False):
    """
    Build Redis Sorted Sets ('feed:latest', 'feed:{category}') and Metadata Hashes
    from ArticleStore in safe batch chunks.
    """
    try:
        r = RedisHandle.client()
        if not force and await r.exists("feed:latest"):
            return

        meta_list = article_store.load_all_articles()
        if not meta_list:
            meta_list = article_store.list_articles()

        if log:
            log.db("Priming Redis", f"Indexing {len(meta_list)} articles into Redis ZSETs & Hashes")

        batch_size = 100
        for i in range(0, len(meta_list), batch_size):
            chunk = meta_list[i : i + batch_size]
            pipe = r.pipeline()
            for meta in chunk:
                if not isinstance(meta, dict) or not meta.get("id"):
                    continue
                aid = meta["id"]
                clean_meta = _strip_heavy_fields(meta)
                ts = get_publication_timestamp(meta)
                cat = str(meta.get("category") or "general").strip().lower()
                pop = float(meta.get("popularity", 0))

                pipe.set(f"article:meta:{aid}", json.dumps(clean_meta))
                pipe.zadd("feed:latest", {aid: ts})
                pipe.zadd(f"feed:{cat}", {aid: ts})
                pipe.zadd("feed:trending", {aid: pop})
            await pipe.execute()

        await r.delete("cache:feed:default")

        if log:
            log.db("Redis Primed", f"Successfully indexed {len(meta_list)} articles")
    except Exception as e:
        if log:
            log.warn(f"Redis indexing failed: {e}")


async def sync_article_to_redis(article: dict):
    """Event-driven sync: update single article metadata hash & ZSETs in Redis on save."""
    try:
        r = RedisHandle.client()
        aid = article.get("id") or article_store.compute_article_id(
            article.get("title", ""), article.get("publication_date", "")
        )
        clean_meta = _strip_heavy_fields(article)
        ts = get_publication_timestamp(article)
        cat = str(article.get("category") or "general").strip().lower()
        pop = float(article.get("popularity", 0))

        pipe = r.pipeline()
        pipe.set(f"article:meta:{aid}", json.dumps(clean_meta))
        pipe.zadd("feed:latest", {aid: ts})
        pipe.zadd(f"feed:{cat}", {aid: ts})
        pipe.zadd("feed:trending", {aid: pop})
        pipe.delete("cache:feed:default")
        await pipe.execute()
    except Exception:
        pass


async def get_all_articles(user_profile: dict | None = None):
    """
    Fast Redis ZSET + Hash retrieval of feeds.
    Unauthenticated users get top 20 from 'feed:latest' ZSET instantly.
    Authenticated users get personalized rankings with cached recommendation scores.
    """
    user_email = user_profile.get("email") if user_profile else None

    # Check recommendation cache for authenticated user
    if user_email:
        rec_key = f"recommendation:user:{user_email}"
        try:
            cached_rec = await RedisHandle.client().get(rec_key)
            if cached_rec:
                return json.loads(cached_rec)
        except Exception:
            pass
    else:
        # Check default feed cache
        try:
            cached_feed = await RedisHandle.client().get("cache:feed:default")
            if cached_feed:
                return json.loads(cached_feed)
        except Exception:
            pass

    # Ensure Redis ZSET is primed
    await prime_redis_indexes()

    # Attempt ultra-fast ZSET + Hash retrieval from Redis
    try:
        r = RedisHandle.client()
        aids = await r.zrevrange("feed:latest", 0, 99)
        if aids:
            pipe = r.pipeline()
            for aid in aids:
                pipe.get(f"article:meta:{aid}")
            meta_strings = await pipe.execute()

            clean_articles = []
            for idx, s in enumerate(meta_strings):
                aid = aids[idx]
                item = None
                if s:
                    try:
                        item = json.loads(s)
                    except Exception:
                        pass

                # If item is missing image metadata, reload full article from Blob Store
                if not item or (isinstance(item, dict) and not item.get("image_url") and not (isinstance(item.get("source"), dict) and (item["source"].get("image_url") or item["source"].get("media")))):
                    full_art = article_store.load_article(aid)
                    if full_art and isinstance(full_art, dict):
                        item = _strip_heavy_fields(full_art)
                        await r.set(f"article:meta:{aid}", json.dumps(item))

                if item:
                    clean_articles.append(item)

            if clean_articles:
                if not user_profile:
                    res = {"feeds": clean_articles[:20]}
                    try:
                        await r.set("cache:feed:default", json.dumps(res), ex=300)
                    except Exception:
                        pass
                    return res

                preferences = user_profile.get("preferences", [])
                raw_weights = user_profile.get("bias", {})
                interactions = user_profile.get("category_scores", {cat: (0, 0.0) for cat in preferences})

                personalized = sort_articles(preferences, raw_weights, interactions, clean_articles)
                res = {"feeds": personalized[:20]}
                try:
                    await r.set(f"recommendation:user:{user_email}", json.dumps(res), ex=1800)
                except Exception:
                    pass
                return res
    except Exception:
        pass

    # Fallback if Redis ZSET not available: load directly from article_store
    raw = article_store.load_all_articles()
    cleaned = [_strip_heavy_fields(art) if isinstance(art, dict) else art for art in raw]
    cleaned.sort(key=get_publication_timestamp, reverse=True)

    if not user_profile:
        res = {"feeds": cleaned[:20]}
        try:
            await RedisHandle.client().set("cache:feed:default", json.dumps(res), ex=300)
        except Exception:
            pass
        return res

    preferences = user_profile.get("preferences", [])
    raw_weights = user_profile.get("bias", {})
    interactions = user_profile.get("category_scores", {cat: (0, 0.0) for cat in preferences})

    personalized = sort_articles(preferences, raw_weights, interactions, cleaned)
    res = {"feeds": personalized[:20]}
    try:
        await RedisHandle.client().set(f"recommendation:user:{user_email}", json.dumps(res), ex=1800)
    except Exception:
        pass
    return res


async def get_article_by_id(article_id: str, user_email: str | None = None):
    """
    Cache-Aside Flow:
    1. Check Redis 'article:body:{article_id}'
    2. If miss, load from Azure Blob/FileStore
    3. Store in Redis with 12-hour TTL
    4. Record user reading history list 'history:user:{email}' (LTRIM 0 99)
    """
    body_key = f"article:body:{article_id}"
    r = None
    try:
        r = RedisHandle.client()
        cached_body = await r.get(body_key)
        if cached_body:
            article = json.loads(cached_body)
            clean_art = _clean_single_article(article)
            if user_email:
                await r.lpush(f"history:user:{user_email}", article_id)
                await r.ltrim(f"history:user:{user_email}", 0, 99)
            return clean_art
    except Exception:
        pass

    article = article_store.load_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    article = _clean_single_article(article)
    article["popularity"] = article.get("popularity", 0) + 1
    if "_id" in article:
        article["_id"] = str(article["_id"])
    else:
        article["_id"] = article_id

    # Cache-Aside: Save article body in Redis with 12-hour TTL
    if r:
        try:
            await r.set(body_key, json.dumps(article), ex=43200)
            await r.zincrby("feed:trending", 1, article_id)
            if user_email:
                await r.lpush(f"history:user:{user_email}", article_id)
                await r.ltrim(f"history:user:{user_email}", 0, 99)
        except Exception:
            pass

    return article


async def get_all_articles_pagination(
    user_profile: dict | None = None,
    page: int = 1,
    limit: int = 20,
    category: str | None = None,
) -> PaginatedArticlesResponse:
    skip = (page - 1) * limit
    clean_cat = (category or "").strip().lower()
    if clean_cat == "all":
        clean_cat = ""

    # Ensure Redis ZSET is primed
    await prime_redis_indexes()

    zset_key = f"feed:{clean_cat}" if clean_cat else "feed:latest"

    # Try fast Redis ZSET + Hash retrieval
    total_count = 0
    clean_articles = []
    try:
        r = RedisHandle.client()
        total_zset = await r.zcard(zset_key)
        if total_zset > 0:
            total_count = total_zset
            # For unauthenticated users, slice directly from ZSET for requested page
            # For authenticated users, fetch candidate pool for personalization
            if user_profile:
                aids = await r.zrevrange(zset_key, 0, 499)
            else:
                aids = await r.zrevrange(zset_key, skip, skip + limit - 1)

            if aids:
                pipe = r.pipeline()
                for aid in aids:
                    pipe.get(f"article:meta:{aid}")
                meta_strings = await pipe.execute()

                for idx, s in enumerate(meta_strings):
                    aid = aids[idx]
                    item = None
                    if s:
                        try:
                            item = json.loads(s)
                        except Exception:
                            pass

                    # If item is missing image metadata, reload full article from Blob Store
                    if not item or (isinstance(item, dict) and not item.get("image_url") and not (isinstance(item.get("source"), dict) and (item["source"].get("image_url") or item["source"].get("media")))):
                        full_art = article_store.load_article(aid)
                        if full_art and isinstance(full_art, dict):
                            item = _strip_heavy_fields(full_art)
                            await r.set(f"article:meta:{aid}", json.dumps(item))

                    if item:
                        clean_articles.append(item)
    except Exception:
        pass

    # Fallback to article_store if Redis ZSET retrieval produced no candidate articles
    if not clean_articles:
        raw = article_store.load_all_articles()
        clean_articles = [_strip_heavy_fields(art) if isinstance(art, dict) else art for art in raw]
        total_count = len(clean_articles)

    # Filter by category if explicitly specified and not already filtered by ZSET
    if clean_cat and not user_profile and not clean_articles:
        clean_articles = [
            a for a in clean_articles
            if isinstance(a, dict) and _normalize_cat(a.get("category")) == clean_cat
        ]

    # Apply personalization if user is logged in
    if user_profile:
        preferences = user_profile.get("preferences", [])
        raw_weights = user_profile.get("bias", {})
        interactions = user_profile.get("category_scores", {cat: (0, 0.0) for cat in preferences})
        sorted_articles = sort_articles(preferences, raw_weights, interactions, clean_articles)
        total_count = len(sorted_articles)
        paged = sorted_articles[skip : skip + limit]
    else:
        paged = clean_articles

    has_more = (skip + len(paged)) < total_count

    return {
        "page": page,
        "limit": limit,
        "has_more": has_more,
        "total": total_count,
        "feeds": paged,
    }


_global_search_store = None
_global_doc_map = {}


def get_global_search_store():
    global _global_search_store, _global_doc_map
    if _global_search_store is None:
        from service.rag.base import Document
        from service.rag.factory import create_doc_store

        all_raw = article_store.load_all_articles()
        docs = []
        doc_map = {}
        for art in all_raw:
            if not isinstance(art, dict) or not art.get("title"):
                continue
            aid = art.get("id") or article_store.compute_article_id(
                art.get("title", ""), art.get("publication_date", "")
            )
            art["id"] = aid
            doc_map[aid] = art

            doc_text = f"{art.get('title', '')}\n{art.get('summary', '')}\n{art.get('content', '')[:1000]}"
            metadata = {
                "id": aid,
                "category": art.get("category", ""),
                "embedding": art.get("embedding") or art.get("vector") or [],
            }
            docs.append(Document(title=art.get("title", ""), content=doc_text, metadata=metadata))

        store = create_doc_store(backend="memory")
        store.upload(docs)
        _global_doc_map = doc_map
        _global_search_store = store

    return _global_search_store, _global_doc_map


async def search_articles(
    query: str,
    page: int = 1,
    limit: int = 20,
    category: str | None = None,
) -> PaginatedArticlesResponse:
    """
    Semantic Embedding-Based Article Search.
    Indexes all processed article vectors in an InMemoryVectorStore once and computes
    cosine similarity for search queries instantly.
    """
    clean_query = (query or "").strip()
    clean_cat = (category or "").strip().lower()
    if clean_cat == "all":
        clean_cat = ""

    if not clean_query:
        return await get_all_articles_pagination(page=page, limit=limit, category=category)

    cache_key = f"cache:search:{clean_query.lower()}:{clean_cat}:{page}:{limit}"
    try:
        r = RedisHandle.client()
        cached = await r.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass

    store, doc_map = get_global_search_store()
    if not doc_map:
        return {
            "page": page,
            "limit": limit,
            "has_more": False,
            "total": 0,
            "feeds": [],
        }

    search_results = store.search(clean_query, limit=100)

    matching_articles = []
    seen_ids = set()

    for sr in search_results:
        aid = sr.metadata.get("id")
        if aid and aid in doc_map and aid not in seen_ids:
            seen_ids.add(aid)
            cm = _strip_heavy_fields(doc_map[aid])
            matching_articles.append(cm)

    # Lexical keyword fallback for higher recall
    query_terms = [t.lower() for t in clean_query.split() if len(t) > 1]
    if query_terms:
        for aid, art in doc_map.items():
            if aid in seen_ids:
                continue
            text = f"{art.get('title', '')} {art.get('summary', '')} {art.get('category', '')} {' '.join(art.get('tags', []))}".lower()
            if any(term in text for term in query_terms):
                seen_ids.add(aid)
                cm = _strip_heavy_fields(art)
                matching_articles.append(cm)

    if clean_cat:
        matching_articles = [art for art in matching_articles if str(art.get("category") or "").strip().lower() == clean_cat]

    skip = (page - 1) * limit
    paged = matching_articles[skip : skip + limit]
    total = len(matching_articles)
    has_more = (skip + len(paged)) < total

    res = {
        "page": page,
        "limit": limit,
        "has_more": has_more,
        "total": total,
        "feeds": paged,
    }

    try:
        await RedisHandle.client().set(cache_key, json.dumps(res), ex=300)
    except Exception:
        pass

    return res
