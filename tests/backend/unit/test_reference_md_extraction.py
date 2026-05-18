"""
Archivo: test_reference_md_extraction.py
Modificación: 2026-05-18
Autor: AgriSearch Team

Descripción:
Tests unitarios para la extracción de referencias desde Markdown parseado.

Acciones Principales:
    - Validar extract_references_from_markdown() con DOIs, títulos, años.
    - Verificar detección de secciones References/Referencias/Bibliography.
    - Confirmar que retorna lista vacía sin sección de referencias.
    - Validar _parse_reference_block() con diferentes formatos.
    - Test de build_reference_batch_from_md() con mocks.

Ejemplo de Ejecución:
    pytest tests/backend/unit/test_reference_md_extraction.py -v
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


# ──────────────────────────────────────────────
# Tests de extract_references_from_markdown
# ──────────────────────────────────────────────

class TestExtractReferencesFromMarkdown:
    """Tests de extracción de referencias desde Markdown."""

    def test_extract_dois_from_references_section(self, tmp_path):
        """Extrae DOIs de la sección References."""
        md_content = """# Paper Title

## Introduction
Some text here.

## Methods
More text.

## References

1. Smith J., Jones K. "Deep learning for agriculture". Nature, 2020. doi: 10.1038/s41586-020-0001

2. Brown L. et al. "Crop yield prediction". Science, 2019. doi: 10.1126/science.1234567
"""
        md_path = tmp_path / "test.md"
        md_path.write_text(md_content, encoding="utf-8")
        
        from app.services.reference_extractor import extract_references_from_markdown
        refs = extract_references_from_markdown(md_path)
        
        assert len(refs) >= 2
        dois = [r["cited_doi"] for r in refs]
        assert any("10.1038" in d for d in dois)
        assert any("10.1126" in d for d in dois)

    def test_no_references_section_returns_empty(self, tmp_path):
        """Sin sección de referencias retorna lista vacía."""
        md_path = tmp_path / "test.md"
        md_path.write_text("# Content\nNo references here.", encoding="utf-8")
        
        from app.services.reference_extractor import extract_references_from_markdown
        refs = extract_references_from_markdown(md_path)
        assert refs == []

    def test_referencias_section_spanish(self, tmp_path):
        """Detecta sección 'Referencias' en español."""
        md_content = """## Referencias

1. García M. "Título del artículo". Revista Agronomía, 2021. doi: 10.5678/test
"""
        md_path = tmp_path / "test.md"
        md_path.write_text(md_content, encoding="utf-8")
        
        from app.services.reference_extractor import extract_references_from_markdown
        refs = extract_references_from_markdown(md_path)
        assert len(refs) == 1
        assert refs[0]["cited_doi"] == "10.5678/test"

    def test_bibliography_section(self, tmp_path):
        """Detecta sección 'Bibliography'."""
        md_content = """## Bibliography

Smith, J. (2020). "A great paper". doi: 10.1111/biblio-test
"""
        md_path = tmp_path / "test.md"
        md_path.write_text(md_content, encoding="utf-8")
        
        from app.services.reference_extractor import extract_references_from_markdown
        refs = extract_references_from_markdown(md_path)
        assert len(refs) == 1

    def test_extraction_source_is_markdown_parse(self, tmp_path):
        """El source se marca como 'markdown_parse'."""
        md_content = "## References\n\n1. Test. doi: 10.1111/test\n"
        md_path = tmp_path / "test.md"
        md_path.write_text(md_content, encoding="utf-8")
        
        from app.services.reference_extractor import extract_references_from_markdown
        refs = extract_references_from_markdown(md_path)
        assert refs[0]["extraction_source"] == "markdown_parse"

    def test_nonexistent_file_returns_empty(self, tmp_path):
        """Archivo inexistente retorna lista vacía."""
        from app.services.reference_extractor import extract_references_from_markdown
        refs = extract_references_from_markdown(tmp_path / "nonexistent.md")
        assert refs == []

    def test_year_extraction(self, tmp_path):
        """Extrae año correctamente."""
        md_content = "## References\n\n1. Smith. 'Paper'. 2020. doi: 10.1111/test\n"
        md_path = tmp_path / "test.md"
        md_path.write_text(md_content, encoding="utf-8")
        
        from app.services.reference_extractor import extract_references_from_markdown
        refs = extract_references_from_markdown(md_path)
        assert refs[0]["cited_year"] == "2020"

    def test_multiple_dois_in_same_block(self, tmp_path):
        """Bloque con múltiples DOIs extrae el primero."""
        md_content = """## References

1. Smith. "Paper A". doi: 10.1111/first Also see doi: 10.2222/second

"""
        md_path = tmp_path / "test.md"
        md_path.write_text(md_content, encoding="utf-8")
        
        from app.services.reference_extractor import extract_references_from_markdown
        refs = extract_references_from_markdown(md_path)
        assert len(refs) == 1
        assert "10.1111/first" in refs[0]["cited_doi"]

    def test_reference_section_stops_at_next_heading(self, tmp_path):
        """La sección de referencias se detiene en el próximo heading."""
        md_content = """## References

1. Smith. "Paper". doi: 10.1111/test

## Appendix
This should not be included. doi: 10.9999/appendix
"""
        md_path = tmp_path / "test.md"
        md_path.write_text(md_content, encoding="utf-8")
        
        from app.services.reference_extractor import extract_references_from_markdown
        refs = extract_references_from_markdown(md_path)
        dois = [r["cited_doi"] for r in refs]
        assert "10.9999/appendix" not in dois


# ──────────────────────────────────────────────
# Tests de _parse_reference_block
# ──────────────────────────────────────────────

class TestParseReferenceBlock:
    """Tests del parser de bloques individuales."""

    def test_parse_doi_and_year(self):
        """Parsea DOI y año de un bloque."""
        from app.services.reference_extractor import _parse_reference_block
        block = '1. Smith J. "Title". 2020. doi: 10.1234/test'
        result = _parse_reference_block(block)
        assert result["cited_doi"] == "10.1234/test"
        assert result["cited_year"] == "2020"

    def test_parse_returns_none_without_doi(self):
        """Retorna None si no hay DOI."""
        from app.services.reference_extractor import _parse_reference_block
        block = "1. Smith J. Some paper without doi."
        result = _parse_reference_block(block)
        assert result is None

    def test_parse_quoted_title(self):
        """Extrae título entre comillas."""
        from app.services.reference_extractor import _parse_reference_block
        block = '1. Smith. "A very long and descriptive title here". 2021. doi: 10.1111/t'
        result = _parse_reference_block(block)
        assert "descriptive title" in result["cited_title"]


# ──────────────────────────────────────────────
# Tests de build_reference_batch_from_md
# ──────────────────────────────────────────────

class TestBuildReferenceBatchFromMD:
    """Tests del batch de extracción desde MD."""

    @pytest.mark.asyncio
    async def test_batch_extracts_from_md_files(self, tmp_path):
        """Extrae referencias de archivos MD de artículos."""
        from app.services.reference_extractor import build_reference_batch_from_md
        
        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        
        mock_article = MagicMock()
        mock_article.id = "art-001"
        mock_article.doi = "10.1111/source"
        mock_article.local_md_path = str(tmp_path / "article.md")
        
        md_content = "## References\n\n1. Test. doi: 10.2222/ref\n"
        (tmp_path / "article.md").write_text(md_content, encoding="utf-8")
        
        with patch("app.services.graph_service.get_eligible_articles_for_graphs", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [mock_article]
            
            stats = await build_reference_batch_from_md("proj-001", mock_session, "all")
            
            assert stats["total_articles"] == 1
            assert stats["articles_with_md"] == 1
            assert stats["total_references_extracted"] >= 1

    @pytest.mark.asyncio
    async def test_batch_skips_articles_without_md(self):
        """Artículos sin MD se saltan."""
        from app.services.reference_extractor import build_reference_batch_from_md
        
        mock_session = AsyncMock()
        
        mock_article = MagicMock()
        mock_article.id = "art-001"
        mock_article.doi = "10.1111/source"
        mock_article.local_md_path = None
        
        with patch("app.services.graph_service.get_eligible_articles_for_graphs", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [mock_article]
            
            stats = await build_reference_batch_from_md("proj-001", mock_session, "all")
            
            assert stats["articles_with_md"] == 0

    @pytest.mark.asyncio
    async def test_batch_handles_missing_md_file(self, tmp_path):
        """Archivo MD inexistente se maneja sin error."""
        from app.services.reference_extractor import build_reference_batch_from_md
        
        mock_session = AsyncMock()
        
        mock_article = MagicMock()
        mock_article.id = "art-001"
        mock_article.doi = "10.1111/source"
        mock_article.local_md_path = str(tmp_path / "nonexistent.md")
        
        with patch("app.services.graph_service.get_eligible_articles_for_graphs", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [mock_article]
            
            stats = await build_reference_batch_from_md("proj-001", mock_session, "all")
            
            # El artículo tiene local_md_path pero el archivo no existe
            # Debería contar como articles_with_md=0 porque el archivo no existe
            assert stats["articles_with_md"] == 0
            assert stats["total_references_extracted"] == 0
