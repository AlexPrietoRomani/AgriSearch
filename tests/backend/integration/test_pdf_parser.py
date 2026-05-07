"""
Archivo: test_pdf_parser.py
Modificación: 2026-05-06
Autor: Alex Prieto

Descripción:
Pruebas de integración para el servicio de parseo de PDFs (`pdf_parser`).
Valida tanto la lógica interna de aplanamiento de tablas (`TableFlattener`)
como el proceso de conversión real de archivos PDF a Markdown enriquecido.

Acciones Principales:
    - Validación del aplanamiento de tablas Markdown a texto atómico.
    - Prueba de parseo de un archivo PDF real del sistema de archivos.
    - Verificación de la persistencia del estado (`parsed_status`) y la creación 
      de archivos Markdown locales.
    - Validación del contenido del archivo Markdown generado (metadatos YAML).

Entradas / Dependencias:
    - Archivos PDF de prueba en `data/projects/`.
    - `pdf_parser` y `TableFlattener` del servicio de documentos.
    - Sesión de base de datos (SQLAlchemy).

Ejemplo de Ejecución:
    pytest tests/backend/integration/test_pdf_parser.py
"""

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Article
from app.services.pdf_parser import TableFlattener, pdf_parser


@pytest.mark.asyncio
async def test_table_flattener_basic():
    """
    Verifica la lógica de TableFlattener con una tabla Markdown de ejemplo.
    """
    md_with_table = (
        "Texto antes de la tabla.\n\n"
        "| Variable | Value | Unit |\n"
        "|---|---|---|\n"
        "| Temperature | 25.5 | C |\n"
        "| Humidity | 60 | % |\n\n"
        "Texto después."
    )
    meta = {"title": "Test Doc", "year": "2024"}
    
    result = TableFlattener.flatten(md_with_table, meta)
    
    assert "Según Test Doc (2024), Variable: Temperature, Value: 25.5, Unit: C." in result
    assert "Según Test Doc (2024), Variable: Humidity, Value: 60, Unit: %." in result
    assert "| Variable |" not in result


@pytest.mark.asyncio
async def test_pdf_parse_real_file(db_session: AsyncSession):
    """
    Verifica el parseo de un archivo PDF real desde el directorio de datos.
    """
    # Usamos un archivo conocido para pruebas de integración
    sample_pdf = Path("data/projects/75e9f074-593d-4c64-a9f8-71691ae1bb70/pdfs/Alreshidi_2019.pdf")
    
    if not sample_pdf.exists():
        pytest.skip(f"Archivo PDF de prueba no encontrado en {sample_pdf}")

    # Crear artículo de prueba
    article = Article(
        id="test-article-id",
        project_id="75e9f074-593d-4c64-a9f8-71691ae1bb70",
        title="Alreshidi 2019 Study",
        authors="Alreshidi et al.",
        year=2019,
        local_pdf_path=str(sample_pdf),
        source_database="arxiv"
    )
    
    # Mock de la DB para evitar efectos secundarios en la integración de lógica
    mock_db = MagicMock()

    success = await pdf_parser.parse_article(article, mock_db)
    
    assert success is True
    assert article.parsed_status == "success"
    assert article.local_md_path is not None
    assert os.path.exists(article.local_md_path)
    
    # Validar estructura del contenido generado
    with open(article.local_md_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "---" in content
        assert "agrisearch_id: test-article-id" in content
        assert "title: Alreshidi 2019 Study" in content
        assert len(content) > 100
