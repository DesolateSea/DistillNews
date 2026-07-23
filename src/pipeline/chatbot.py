"""
Chatbot pipeline.

Handles keyword extraction, RAG document search, and conversational
response generation using abstract agent and document store providers.

Replaces the old ``src/julep/run_chatbot.py``.
"""

import json
import os
import sys
from pathlib import Path
from collections import deque, defaultdict

from agents import create_agent
from rag import create_doc_store
from rag.base import Document

from pipeline.logger import log

# Resolve directories relative to src/
SRC_DIR = Path(__file__).resolve().parent.parent
prompts_dir = SRC_DIR / "prompts"
processed_dir = SRC_DIR / "data" / "processed"

# Create shared instances (providers selected by env vars)
agent = create_agent()
doc_store = create_doc_store()

# Per-user conversation memory (in-memory, capped at 6 messages)
user_memory = defaultdict(lambda: deque(maxlen=6))


def _load_and_upload_articles(folder_path=None):
    """Load processed articles from JSON and upload to the document store."""
    folder_path = folder_path or processed_dir
    documents = []

    log.section("RAG Document Upload")
    log.info("Scanning for articles", str(folder_path))

    for root, _, files in os.walk(folder_path):
        for file in files:
            if not file.endswith(".json"):
                continue
            with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                data = json.load(f)
            if "content" in data:
                documents.append(
                    Document(
                        title=data["title"],
                        content=data["content"],
                        metadata={
                            "tags": data.get("tags", []),
                            "location": data.get("location", ""),
                            "category": data.get("category", ""),
                            "publication_date": data.get("publication_date", ""),
                        },
                    )
                )

    # Create an aggregate "all news" document for broad queries
    if documents:
        all_titles = [doc.title for doc in documents]
        documents.append(
            Document(
                title="News | All News | Recent News | Latest News | Current News",
                content="\n\n".join(all_titles),
                metadata={"tags": ["News"]},
            )
        )

    if documents:
        doc_store.upload(documents)
        log.success(f"Uploaded {len(documents)} articles to document store")


def _filter_prompts(prompt):
    """Extract keywords from a user query using the filter prompt."""
    log.ai_call("keyword_extraction", prompt)
    result = agent.complete_from_template(
        prompts_dir / "filter_prompt.yaml", {"query": prompt}
    )
    log.ai_result("keyword_extraction", result.content)
    return result.content


def get_chatbot_response(query, user_id="debug", reading=None, prompt="chatbot.yaml"):
    """Generate a chatbot response using RAG-enhanced context.

    1. Extract keywords from the query
    2. Search the document store for relevant articles
    3. Generate a conversational response

    Args:
        query: User's question
        user_id: Unique user identifier for conversation memory
        reading: Article content the user is currently reading (optional)
        prompt: YAML template filename for the chatbot response
    """
    log.chat_query(user_id, query)
    memory = user_memory[user_id]

    # Step 1: Extract keywords
    filtered = _filter_prompts(query)

    # Step 2: Search documents
    search_results = doc_store.search(filtered, limit=5)
    log.rag_search(filtered, len(search_results))

    if not search_results:
        context = "No relevant articles found."
        log.warn("No RAG results for query")
    else:
        context = "\n\n".join(
            r.snippet if r.snippet else r.content for r in search_results
        )

    if not context:
        return None

    # Step 3: Generate response
    log.ai_call("chatbot_response", query)
    result = agent.complete_from_template(
        prompts_dir / prompt,
        {
            "query": query,
            "reading": reading or "",
            "content": context,
            "memory": "\n".join(memory),
        },
    )

    response = result.content
    log.chat_response(response)

    # Update conversation memory
    memory.append(f"User: {query}")
    memory.append(f"Assistant: {response}")

    with open("debug.log", "a") as f:
        f.write(f"User: {user_id}\nMemory: {' '.join(memory)}\n")

    return response


# Upload articles on first import (lazy init)
_articles_uploaded = False


def ensure_articles_uploaded():
    """Upload articles to document store if not already done."""
    global _articles_uploaded
    if not _articles_uploaded:
        _load_and_upload_articles()
        _articles_uploaded = True


if __name__ == "__main__":
    ensure_articles_uploaded()
    while True:
        query = input("\n>> ")
        res = get_chatbot_response(query)
