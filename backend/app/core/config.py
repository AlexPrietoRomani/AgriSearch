"""
AgriSearch Backend - Core Configuration.

Centralized settings using Pydantic Settings for type-safe environment variable management.
"""

from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


import re
import unicodedata

def sanitize_folder_name(name: str) -> str:
    """Sanitizes strings for folder names (removes accents, spaces -> underscores)."""
    if not name:
        return "Desconocido"
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8')
    name = re.sub(r'[^\w\s-]', '', name)
    return re.sub(r'[\s-]+', '_', name.strip())

class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Application ---
    app_name: str = "AgriSearch"
    app_version: str = "0.1.0"
    debug: bool = True

    # --- Paths ---
    base_data_dir: Path = Path("data/projects")
    vector_db_dir: Path = Path("vector_db")

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./agrisearch.db"

    # --- CORS ---
    cors_origins: list[str] = ["http://localhost:4321", "http://localhost:3000"]

    # --- LiteLLM / Ollama ---
    litellm_model: str = "ollama/aya:8b"
    litellm_api_base: str = "http://localhost:11434"
    embedding_model: str = "ollama/nomic-embed-text"

    # --- Qdrant ---
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    # --- Search defaults ---
    search_max_results_per_source: int = 200
    search_dedup_threshold: float = 0.85

    # --- API Keys for scientific databases ---
    crossref_mailto: str = "agrisearch@example.com"
    core_api_key: str = ""
    redalyc_token: str = ""
    openalex_key: str = ""
    semantic_scholar_key: str = ""

    # --- Download ---
    download_rate_limit: int = 10  # requests per second
    download_timeout: int = 30  # seconds per PDF

    def get_project_data_dir(self, project_id: str, project_name: str | None = None) -> Path:
        """Return the data directory for a specific project."""
        if project_name:
            path = self.base_data_dir / sanitize_folder_name(project_name)
        else:
            path = self.base_data_dir / project_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_project_pdfs_dir(self, project_id: str, project_name: str | None = None, search_name: str | None = None) -> Path:
        """Return the PDFs directory for a specific project."""
        base = self.get_project_data_dir(project_id, project_name)
        if search_name:
            path = base / sanitize_folder_name(search_name) / "descargas"
        else:
            path = base / "pdfs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_project_raw_dir(self, project_id: str, project_name: str | None = None) -> Path:
        """Return the raw CSV directory for a specific project."""
        if project_name:
            path = self.get_project_data_dir(project_id, project_name) / "raw"
        else:
            path = self.get_project_data_dir(project_id) / "raw"
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    """Cached singleton for application settings."""
    return Settings()
