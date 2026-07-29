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

    @property
    def EMBEDDING_SERVICE_URL(self) -> str:
        return os.getenv("EMBEDDING_SERVICE_URL", "http://embedding-server:8001")

    # ------------------------------------------------------------------
    # Article Store Settings
    # ------------------------------------------------------------------

    @property
    def ARTICLE_STORE_BACKEND(self) -> str:
        """Backend for processed article persistence.

        Options: ``file`` (local disk, default), ``azure`` (Azure Blob Storage).
        """
        return os.getenv("ARTICLE_STORE_BACKEND", "file")

    @property
    def AZURE_STORAGE_CONNECTION_STRING(self) -> str | None:
        """Azure Storage account connection string for Blob Storage."""
        return os.getenv("AZURE_STORAGE_CONNECTION_STRING")

    @property
    def AZURE_BLOB_CONTAINER(self) -> str:
        """Azure Blob container name for processed articles."""
        return os.getenv("AZURE_BLOB_CONTAINER", "processed-articles")

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

    def set_source_enabled(self, source_name: str, enabled: bool) -> None:
        """Dynamically enable or disable a pipeline source at runtime."""
        name = source_name.strip().lower()
        disabled = self.DISABLED_PIPELINE_SOURCES
        if enabled:
            disabled.discard(name)
        else:
            disabled.add(name)
        os.environ["DISABLED_PIPELINE_SOURCES"] = ",".join(sorted(disabled))

        if self.ENABLED_PIPELINE_SOURCES is not None:
            enabled_set = self.ENABLED_PIPELINE_SOURCES
            if enabled:
                enabled_set.add(name)
            else:
                enabled_set.discard(name)
            os.environ["ENABLED_PIPELINE_SOURCES"] = ",".join(sorted(enabled_set))

    def toggle_source(self, source_name: str) -> bool:
        """Toggle a pipeline source between enabled and disabled at runtime. Returns new status."""
        new_status = not self.is_source_enabled(source_name)
        self.set_source_enabled(source_name, new_status)
        return new_status

    @property
    def DEBUG(self) -> bool:
        """Returns True if DEBUG environment variable is enabled ('true', '1', 'yes')."""
        return os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

    def is_debug(self) -> bool:
        """Check whether application debug mode is enabled."""
        return self.DEBUG


# Shared singleton configuration instance
config = Config()

