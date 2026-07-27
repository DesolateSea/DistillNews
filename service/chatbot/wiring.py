"""Pipeline wiring for article ingestion and the provider-neutral chatbot."""

from pathlib import Path

<<<<<<< HEAD:backend/chatbot/wiring.py
from agents import create_agent
from db import FileStore
from chatbot.service import ChatbotService
from chatbot.rag import create_doc_store
from utils.logger import log
=======
from service.agents import create_agent
from service.db import FileStore
from service.chatbot.service import ChatbotService
from service.rag import create_doc_store
from service.rag.base import Document

from service.logger import log
>>>>>>> 582a92f (refactor: The code base has sperated the pipelines completely from the):service/chatbot/wiring.py

prompts_dir = Path(__file__).resolve().parent / "prompts"

# Provider selection happens at the boundaries. The chatbot service itself is
# unaware of the chat model, document store, and embedding implementation.
agent = create_agent()
doc_store = create_doc_store()
chatbot = ChatbotService(agent, doc_store, prompts_dir, logger=log)


def _load_and_upload_articles():
    """Load processed articles via FileStore repository and upload to document store."""
    documents = []

    log.section("RAG Document Upload")
    files = FileStore.list_processed_files()
    log.info("Scanning for articles via FileStore", f"{len(files)} files found")

    for file in files:
        data = FileStore.read_json(file)
        if isinstance(data, dict) and "content" in data:
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

    if documents:
        documents.append(
            Document(
                title="News | All News | Recent News | Latest News | Current News",
                content="\n\n".join(document.title for document in documents),
                metadata={"tags": ["News"]},
            )
        )
        doc_store.upload(documents)
        log.success(f"Uploaded {len(documents)} articles to document store")


def get_chatbot_response(query, user_id="debug", reading=None, prompt="chatbot.yaml"):
    """Delegate a query to the chatbot service."""
    return chatbot.get_response(
        query=query,
        user_id=user_id,
        reading=reading,
        prompt=prompt,
    )


_articles_uploaded = False


def ensure_articles_uploaded():
    """Upload articles once for this running process."""
    global _articles_uploaded
    if not _articles_uploaded:
        _load_and_upload_articles()
        _articles_uploaded = True


if __name__ == "__main__":
    ensure_articles_uploaded()
    while True:
        query = input("\n>> ")
        print(get_chatbot_response(query))
