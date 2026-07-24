"""
Centralized Configuration Module.

All environment variable lookups and runtime defaults across the application
are centralized in this module.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

root_env = Path(__file__).resolve().parent.parent / ".env"
backend_env = Path(__file__).resolve().parent / ".env"
if backend_env.exists():
    load_dotenv(backend_env)
elif root_env.exists():
    load_dotenv(root_env)
else:
    load_dotenv()



class Config:
    """Central configuration class providing property accessors for environment variables."""

    # ------------------------------------------------------------------
    # Agent & RAG Provider Settings
    # ------------------------------------------------------------------

    @property
    def AGENT_PROVIDER(self) -> str:
        return os.getenv("AGENT_PROVIDER", "openai")

    @property
    def RAG_BACKEND(self) -> str:
        # Keep retrieval opt-in so starting a service does not unexpectedly
        # make embedding requests. Use ``memory`` for the local in-process
        # vector store, or ``julep`` for Julep-managed retrieval.
        return os.getenv("RAG_BACKEND", "none")

    @property
    def EMBEDDING_PROVIDER(self) -> str:
        """Provider used by the in-memory vector store.

        This is intentionally independent of ``AGENT_PROVIDER``. For example,
        a chatbot can use a Foundry chat model while creating embeddings with
        a local Ollama model.
        """
        return os.getenv("EMBEDDING_PROVIDER", "none")

    # OpenAI / Foundry Provider
    @property
    def OPENAI_API_KEY(self) -> str | None:
        return os.getenv("FOUNDRY_API_KEY") or os.getenv("OPENAI_API_KEY")

    @property
    def OPENAI_MODEL(self) -> str:
        return (
            os.getenv("AGENT_MODEL")
            or os.getenv("FOUNDRY_MODEL")
            or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        )

    @property
    def OPENAI_BASE_URL(self) -> str | None:
        return os.getenv("FOUNDRY_BASE_URL") or os.getenv("OPENAI_BASE_URL")

    @property
    def OPENAI_EMBEDDING_MODEL(self) -> str:
        return (
            os.getenv("FOUNDRY_EMBEDDING_MODEL")
            or os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        )

    # Julep Provider
    @property
    def JULEP_API_KEY(self) -> str | None:
        return os.getenv("JULEP_API_KEY")

    @property
    def JULEP_MODEL(self) -> str:
        return (
            os.getenv("AGENT_MODEL")
            or os.getenv("JULEP_MODEL", "claude-3.5-sonnet")
        )

    @property
    def JULEP_ENVIRONMENT(self) -> str:
        return os.getenv("JULEP_ENVIRONMENT", "production")

    # ------------------------------------------------------------------
    # Ollama Local Settings
    # ------------------------------------------------------------------

    @property
    def OLLAMA_BASE_URL(self) -> str:
        return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    @property
    def OLLAMA_MODEL(self) -> str:
        return os.getenv("OLLAMA_MODEL", "llama3")

    @property
    def OLLAMA_EMBEDDING_MODEL(self) -> str:
        return os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

    # ------------------------------------------------------------------
    # Local Sentence Transformers Settings
    # ------------------------------------------------------------------

    @property
    def SENTENCE_TRANSFORMERS_EMBEDDING_MODEL(self) -> str:
        return os.getenv(
            "SENTENCE_TRANSFORMERS_EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        )

    @property
    def SENTENCE_TRANSFORMERS_DEVICE(self) -> str | None:
        """Optional Torch device override, such as ``cpu``, ``cuda``, or ``mps``."""
        return os.getenv("SENTENCE_TRANSFORMERS_DEVICE")

    # ------------------------------------------------------------------
    # HuggingFace Settings
    # ------------------------------------------------------------------

    @property
    def HUGGINGFACE_API_KEY(self) -> str | None:
        return os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN")

    @property
    def HUGGINGFACE_MODEL(self) -> str:
        return os.getenv("HUGGINGFACE_MODEL", "meta-llama/Llama-3.2-3B-Instruct")

    @property
    def HUGGINGFACE_EMBEDDING_MODEL(self) -> str:
        return os.getenv("HUGGINGFACE_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

    # ------------------------------------------------------------------
    # News API Sources Keys
    # ------------------------------------------------------------------

    @property
    def CORE_API_KEY(self) -> str | None:
        return os.getenv("CORE_API_KEY")

    @property
    def GNEWS_API_KEY(self) -> str | None:
        return os.getenv("GNEWS_API_KEY")

    @property
    def MEDIASTACK_API_KEY(self) -> str | None:
        return os.getenv("MEDIASTACK_API_KEY")

    @property
    def NEWS_API_KEY(self) -> str | None:
        return os.getenv("NEWS_API_KEY")

    @property
    def RAPIDAPI_KEY(self) -> str | None:
        return os.getenv("RAPIDAPI_KEY")

    @property
    def REDDIT_CLIENT_ID(self) -> str | None:
        return os.getenv("REDDIT_CLIENT_ID")

    @property
    def REDDIT_SECRET(self) -> str | None:
        return os.getenv("REDDIT_SECRET")

    @property
    def OPENWEATHER_API_KEY(self) -> str | None:
        return os.getenv("OPENWEATHER_API_KEY")

    # ------------------------------------------------------------------
    # Database & Server Settings
    # ------------------------------------------------------------------

    @property
    def DB_URL(self) -> str | None:
        return os.getenv("DB_URL")

    @property
    def JWT_SECRET(self) -> str | None:
        return os.getenv("JWT_SECRET")

    @property
    def REDIS_URL(self) -> str:
        return os.getenv("REDIS_URL", "redis://redis:6379/0")

    # ------------------------------------------------------------------
    # Pipeline Source & Service Controls
    # ------------------------------------------------------------------

    @property
    def DISABLED_PIPELINE_SOURCES(self) -> set[str]:
        """Comma-separated list of pipeline sources/services to disable (e.g., 'reddit,scrape,rapid_news')."""
        raw = os.getenv("DISABLED_PIPELINE_SOURCES", "")
        return {s.strip().lower() for s in raw.split(",") if s.strip()}

    @property
    def ENABLED_PIPELINE_SOURCES(self) -> set[str] | None:
        """Comma-separated list of explicitly enabled pipeline sources/services. If unset, all non-disabled sources are active."""
        raw = os.getenv("ENABLED_PIPELINE_SOURCES")
        if raw is None:
            return None
        return {s.strip().lower() for s in raw.split(",") if s.strip()}

    def is_source_enabled(self, source_name: str) -> bool:
        """Check whether a pipeline source or service (e.g., 'gnews', 'reddit', 'scrape', 'media_stack') is enabled."""
        name = source_name.strip().lower()
        if name in self.DISABLED_PIPELINE_SOURCES:
            return False
        enabled = self.ENABLED_PIPELINE_SOURCES
        if enabled is not None:
            return name in enabled
        return True


# Shared singleton configuration instance
config = Config()

