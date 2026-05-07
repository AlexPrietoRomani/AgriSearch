"""
Archivo: config.py
Modificación: 2026-05-06
Autor: Alex Prieto

Descripción:
Configuración centralizada para el backend de AgriSearch.
Utiliza Pydantic Settings para gestionar variables de entorno de forma segura
y tipada. Proporciona valores predeterminados para la conexión a la base de datos,
modelos de IA, rutas de almacenamiento y claves de API.

Acciones Principales:
    - Define todas las variables de entorno necesarias y sus tipos.
    - Asegura que las rutas de directorios se creen dinámicamente si no existen.
    - Valida y formatea URLs de conexión de base de datos.
    - Sanitiza nombres de carpetas.

Estructura Interna:
    - `sanitize_folder_name`: Función para limpiar strings que se usarán como nombres de directorio.
    - `Settings`: Clase de Pydantic para validar la configuración global.
    - `get_settings`: Instancia Singleton en caché para acceder rápidamente a la configuración.

Entradas / Dependencias:
    - Variables de entorno o el archivo `.env` en la raíz del backend.
    - Módulos estándar (`pathlib`, `re`, `unicodedata`).

Salidas / Efectos:
    - Retorna el objeto `Settings` con todas las rutas y variables preparadas.
    - Puede crear directorios en disco (ej. `data/projects/...`).

Ejemplo de Integración:
    from app.core.config import get_settings
    
    settings = get_settings()
    print(settings.database_url)
    db_path = settings.get_project_data_dir("project_id")
"""

from pathlib import Path
from typing import Any
from functools import lru_cache
import re
import unicodedata
import logging

from pydantic import Field, model_validator, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

def sanitize_folder_name(name: str) -> str:
    """
    Sanitiza un string para usarlo de forma segura como nombre de carpeta.
    Elimina acentos, caracteres especiales y convierte espacios en guiones bajos.

    Args:
        name (str): El nombre original de la carpeta o proyecto.

    Returns:
        str: El nombre limpio y sanitizado. Retorna 'Desconocido' si el string está vacío.
    """
    if not name:
        return "Desconocido"
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8')
    name = re.sub(r'[^\w\s-]', '', name)
    return re.sub(r'[\s-]+', '_', name.strip())

class Settings(BaseSettings):
    """
    Configuración global de la aplicación cargada desde variables de entorno o archivo .env.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )

    # --- Aplicación ---
    app_name: str = "AgriSearch"
    app_version: str = "0.1.0"
    debug: bool = True

    # --- Rutas ---
    base_data_dir: Path = Path("data/projects")
    vector_db_dir: Path = Path("vector_db")

    # --- Base de Datos ---
    database_url: str = Field(
        default="sqlite+aiosqlite:///../agrisearch.db",
        description="URL de conexión para la base de datos SQLAlchemy."
    )

    @model_validator(mode="before")
    @classmethod
    def force_root_db(cls, data: dict[str, Any]) -> dict[str, Any]:
        """
        Fuerza el uso de la base de datos dentro del directorio `backend/data/`.
        Migra la base de datos antigua si se encuentra en la raíz del repositorio.

        Args:
            data (dict[str, Any]): Diccionario con los datos iniciales de configuración.

        Returns:
            dict[str, Any]: Diccionario con la URL de la base de datos corregida/validada.
        """
        # Si se pasó una URL explícita (desde .env), la respetamos
        if data.get("database_url") and not data["database_url"].endswith("agrisearch.db"):
             return data

        # El archivo config.py está en backend/app/core/config.py
        # backend/ está 3 niveles arriba: core -> app -> backend
        backend_root = Path(__file__).resolve().parent.parent.parent
        data_dir = backend_root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path = data_dir / "agrisearch.db"
        
        # Si existe la BD antigua en la raíz del proyecto, migrarla
        old_db_path = backend_root.parent / "agrisearch.db"
        if old_db_path.exists() and not db_path.exists():
            import shutil
            shutil.copy2(old_db_path, db_path)
            logger.info(f"Base de datos migrada desde {old_db_path} hacia {db_path}")
        
        # Fallback a backend/data/ si no hay configuración especial
        if not data.get("database_url") or "agrisearch.db" in data.get("database_url", ""):
            data["database_url"] = f"sqlite+aiosqlite:///{db_path.as_posix()}"
            
        return data

    # --- CORS ---
    cors_origins: list[str] = ["http://localhost:4321", "http://localhost:3000"]

    # --- LiteLLM / Ollama ---
    litellm_model: str = "ollama/gemma4:e4b"
    litellm_api_base: str = "http://localhost:11434"
    embedding_model: str = "ollama/nomic-embed-text-v2-moe:latest"

    # --- Qdrant ---
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    # --- Valores por defecto para búsqueda ---
    search_max_results_per_source: int = 200
    search_dedup_threshold: float = 0.85

    # --- API Keys para bases de datos científicas ---
    crossref_mailto: str = "agrisearch@example.com"
    core_api_key: str = ""
    redalyc_token: str = ""
    openalex_key: str = ""
    semantic_scholar_key: str = ""

    # --- Descargas ---
    download_rate_limit: int = 10  # Peticiones por segundo
    download_timeout: int = 30  # Segundos por PDF

    def get_project_data_dir(self, project_id: str, project_name: str | None = None) -> Path:
        """
        Retorna y crea (si no existe) el directorio principal de datos para un proyecto.

        Args:
            project_id (str): Identificador único del proyecto.
            project_name (str | None, opcional): Nombre del proyecto para una carpeta más legible.

        Returns:
            Path: Ruta al directorio de datos del proyecto.
        """
        if project_name:
            path = self.base_data_dir / sanitize_folder_name(project_name)
        else:
            path = self.base_data_dir / project_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_project_pdfs_dir(self, project_id: str, project_name: str | None = None, search_name: str | None = None) -> Path:
        """
        Retorna y crea el directorio donde se guardarán los PDFs descargados.

        Args:
            project_id (str): Identificador único del proyecto.
            project_name (str | None, opcional): Nombre del proyecto.
            search_name (str | None, opcional): Nombre de una búsqueda específica para crear una subcarpeta.

        Returns:
            Path: Ruta al directorio de los PDFs.
        """
        base = self.get_project_data_dir(project_id, project_name)
        if search_name:
            path = base / sanitize_folder_name(search_name) / "descargas"
        else:
            path = base / "pdfs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_project_raw_dir(self, project_id: str, project_name: str | None = None) -> Path:
        """
        Retorna y crea el directorio para almacenar los archivos crudos (ej. CSV originales).

        Args:
            project_id (str): Identificador único del proyecto.
            project_name (str | None, opcional): Nombre del proyecto.

        Returns:
            Path: Ruta al directorio de datos crudos (raw).
        """
        path = self.get_project_data_dir(project_id, project_name) / "raw"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_project_parsed_dir(self, project_id: str, project_name: str | None = None) -> Path:
        """
        Retorna y crea el directorio para almacenar documentos procesados (ej. Markdown).

        Args:
            project_id (str): Identificador único del proyecto.
            project_name (str | None, opcional): Nombre del proyecto.

        Returns:
            Path: Ruta al directorio de documentos procesados (parsed).
        """
        path = self.get_project_data_dir(project_id, project_name) / "parsed"
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    """
    Singleton en caché para proveer la configuración de la aplicación globalmente.
    
    Returns:
        Settings: Instancia cargada con la configuración actual de las variables de entorno.
    """
    return Settings()
