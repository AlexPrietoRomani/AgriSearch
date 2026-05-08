"""
Archivo: test_system_api.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Suite de pruebas unitarias para los endpoints de información del sistema en la 
API de AgriSearch. Se enfoca en validar la correcta exposición del estado de 
disponibilidad de las bases de datos científicas externas, sus requerimientos 
de autenticación y su capacidad de descarga de documentos.

Acciones Principales:
    - Validación de integridad de la respuesta del endpoint de estado de BDs.
    - Verificación de metadatos mandatorios por cada fuente de datos.
    - Comprobación de lógica de negocio sobre requerimientos de API Keys.
    - Validación de indicadores de descargabilidad.

Estructura Interna:
    - `TestDBStatusEndpoint`: Pruebas funcionales del endpoint `/system/db-status`.

Entradas / Dependencias:
    - `app.main.app`.
    - `fastapi.testclient.TestClient`.

Salidas / Efectos:
    - Valida la consistencia de los esquemas de respuesta del sistema.
    - Reporta el estado de configuración detectado en el entorno de pruebas.

Ejecución:
    pytest tests/backend/unit/test_system_api.py
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


class TestDBStatusEndpoint:
    """Tests del endpoint GET /api/v1/system/db-status."""

    def test_db_status_returns_all_dbs(self):
        """Retorna 9 BDs en la respuesta."""
        response = client.get("/api/v1/system/db-status")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 9

    def test_db_status_has_required_fields(self):
        """Cada BD tiene los campos requeridos."""
        response = client.get("/api/v1/system/db-status")
        data = response.json()
        for db_id, db_info in data.items():
            assert "id" in db_info
            assert "label" in db_info
            assert "requires_key" in db_info
            assert "key_configured" in db_info
            assert "downloadable" in db_info
            assert "note" in db_info
            assert db_info["id"] == db_id

    def test_db_status_core_requires_key(self):
        """CORE requiere API key."""
        response = client.get("/api/v1/system/db-status")
        data = response.json()
        assert data["core"]["requires_key"] is True
        assert data["core"]["downloadable"] is True

    def test_db_status_redalyc_requires_key(self):
        """Redalyc requiere token."""
        response = client.get("/api/v1/system/db-status")
        data = response.json()
        assert data["redalyc"]["requires_key"] is True
        assert data["redalyc"]["downloadable"] is True

    def test_db_status_openalex_no_key(self):
        """OpenAlex no requiere key."""
        response = client.get("/api/v1/system/db-status")
        data = response.json()
        assert data["openalex"]["requires_key"] is False
        assert data["openalex"]["downloadable"] is True

    def test_db_status_arxiv_downloadable(self):
        """ArXiv es descargable (siempre OA)."""
        response = client.get("/api/v1/system/db-status")
        data = response.json()
        assert data["arxiv"]["downloadable"] is True
        assert data["arxiv"]["requires_key"] is False

    def test_db_status_crossref_not_downloadable(self):
        """CrossRef no es descargable directamente (solo DOIs)."""
        response = client.get("/api/v1/system/db-status")
        data = response.json()
        assert data["crossref"]["downloadable"] is False

    def test_db_status_key_configured_reflects_env(self):
        """key_configured refleja si la API key está configurada en env."""
        response = client.get("/api/v1/system/db-status")
        data = response.json()
        # Sin CORE_API_KEY configurado, key_configured debe ser False
        assert data["core"]["key_configured"] is False
        # Sin REDALYC_TOKEN configurado, key_configured debe ser False
        assert data["redalyc"]["key_configured"] is False
