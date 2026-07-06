"""Zentrale Konfiguration aus .env via pydantic-settings.

Keine Secrets im Code. Alle Werte kommen aus Umgebungsvariablen bzw. .env.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Laufzeit-Konfiguration. Feldnamen sind case-insensitive zu den ENV-Keys."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Datenbank. Innerhalb von Compose ist der Host "db", lokal "localhost".
    database_url: str = "postgresql+psycopg://drift:drift@localhost:5432/drift"

    # Anthropic. Nur fuer --mode claude noetig, im Mock-Modus optional.
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"

    # Dimension der pgvector-Spalten (muss zur Migration passen).
    embedding_dim: int = 1024


@lru_cache
def get_settings() -> Settings:
    """Gecachte Settings-Instanz, damit .env nur einmal gelesen wird."""
    return Settings()
