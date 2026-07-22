"""
Centralized Configuration Module.

All environment variable lookups and runtime defaults across the application
are centralized in this module.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root or parent directory
root_env = Path(__file__).resolve().parent.parent / ".env"
if root_env.exists():
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
        return os.getenv("AGENT_PROVIDER", "julep")

    @property
    def RAG_BACKEND(self) -> str:
        return os.getenv("RAG_BACKEND", "julep")

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

    # ------------------------------------------------------------------
    # Database & Server Settings
    # ------------------------------------------------------------------

    @property
    def DB_URL(self) -> str | None:
        return os.getenv("DB_URL")

    @property
    def JWT_SECRET(self) -> str | None:
        return os.getenv("JWT_SECRET")


# Shared singleton configuration instance
config = Config()
