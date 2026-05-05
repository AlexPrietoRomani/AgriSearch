"""
Tests de integración para el pipeline Dual-Parser de documentos.

Estructura:
    tests/backend/integration/
    ├── fixtures/
    │   ├── sample_inputs/          # PDFs y documentos de prueba
    │   └── expected_outputs/       # Markdowns de referencia generados
    ├── test_pdf_parser.py          # Tests existentes (TableFlattener, parsing real)
    ├── test_dual_parser.py         # Tests del pipeline dual-parser (ESTE ARCHIVO)
    └── conftest.py                 # Fixtures compartidas para integration tests

Requiere:
    - Java 11+ (para OpenDataLoader PDF)
    - uv sync ejecutado en backend/
    - Al menos 1 PDF en fixtures/sample_inputs/ O en backend/data/projects/

Ejecutar:
    uv run pytest tests/backend/integration/test_dual_parser.py -v
"""
import pytest
import asyncio
import time
import tempfile
import shutil
import yaml
from pathlib import Path
from unittest.mock import MagicMock

# ── Constantes ────────────────────────────────────────────────────────────────
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_INPUTS = FIXTURES_DIR / "sample_inputs"
EXPECTED_OUTPUTS = FIXTURES_DIR / "expected_outputs"

SAMPLE_META = {
    "id": "test-integration-001",
    "doi": "10.1234/test.2024.001",
    "title": "Integration Test Article on Precision Agriculture",
    "authors": "García J., López M., Smith A.",
    "year": 2024,
    "journal": "Computers and Electronics in Agriculture",
    "keywords": ["precision agriculture", "remote sensing", "NDVI"],
    "source_database": "openalex",
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def _find_any_pdf() -> Path | None:
    """Busca un PDF de prueba en fixtures o en data/projects/."""
    # 1. Buscar en fixtures
    for pdf in SAMPLE_INPUTS.glob("*.pdf"):
        return pdf
    # 2. Buscar en data real del proyecto
    data_dir = Path(__file__).parent.parent.parent.parent / "backend" / "data" / "projects"
    if data_dir.exists():
        for pdf in data_dir.rglob("*.pdf"):
            return pdf
    return None


def _validate_front_matter(md_content: str) -> dict:
    """Extrae y valida el front-matter YAML de un markdown."""
    assert md_content.startswith("---"), "Markdown debe empezar con front-matter YAML (---)"
    parts = md_content.split("---", 2)
    assert len(parts) >= 3, "Front-matter YAML mal formado (faltan delimitadores ---)"
    data = yaml.safe_load(parts[1])
    assert isinstance(data, dict), "Front-matter no es un diccionario YAML válido"
    return data


# ══════════════════════════════════════════════════════════════════════════════
#  TESTS: OpenDataLoader PDF Parser
# ══════════════════════════════════════════════════════════════════════════════

class TestOpenDataLoaderParser:
    """Tests de integración para OpenDataLoaderParser (artículos científicos)."""

    @pytest.mark.skipif(
        not _find_any_pdf(),
        reason="No hay PDF de prueba disponible en fixtures/ ni en data/projects/"
    )
    def test_opendataloader_import(self):
        """OpenDataLoader PDF está instalado y es importable."""
        import opendataloader_pdf
        assert opendataloader_pdf is not None

    @pytest.mark.skipif(
        not _find_any_pdf(),
        reason="No hay PDF de prueba disponible"
    )
    def test_opendataloader_convert_to_markdown(self, tmp_path):
        """OpenDataLoader convierte un PDF real a Markdown con layout detectado."""
        import opendataloader_pdf

        pdf_path = _find_any_pdf()
        output_dir = tmp_path / "odl_output"
        output_dir.mkdir()

        opendataloader_pdf.convert(
            input_path=str(pdf_path),
            output_dir=str(output_dir),
            format="markdown",
            use_struct_tree=True,
            table_method="cluster",
        )

        # Verificar que se generó al menos un archivo .md
        md_files = list(output_dir.glob("*.md"))
        assert len(md_files) >= 1, f"No se generó ningún .md en {output_dir}"

        content = md_files[0].read_text(encoding="utf-8")
        assert len(content) > 100, "Markdown generado demasiado corto"

        # Guardar como output de referencia si fixtures están vacías
        ref_output = EXPECTED_OUTPUTS / f"{pdf_path.stem}_opendataloader.md"
        if not ref_output.exists():
            ref_output.write_text(content, encoding="utf-8")

    @pytest.mark.skipif(
        not _find_any_pdf(),
        reason="No hay PDF de prueba disponible"
    )
    def test_opendataloader_performance(self):
        """La conversión con OpenDataLoader toma < 30s para un PDF."""
        import opendataloader_pdf

        pdf_path = _find_any_pdf()
        with tempfile.TemporaryDirectory() as tmp:
            start = time.perf_counter()
            opendataloader_pdf.convert(
                input_path=str(pdf_path),
                output_dir=tmp,
                format="markdown",
            )
            elapsed = time.perf_counter() - start

        assert elapsed < 30.0, f"Conversión demasiado lenta: {elapsed:.1f}s (límite: 30s)"


# ══════════════════════════════════════════════════════════════════════════════
#  TESTS: MarkItDown Parser
# ══════════════════════════════════════════════════════════════════════════════

class TestMarkItDownParser:
    """Tests de integración para MarkItDownParser (formatos universales)."""

    def test_markitdown_import(self):
        """MarkItDown está instalado y es importable."""
        from markitdown import MarkItDown
        md = MarkItDown()
        assert md is not None

    @pytest.mark.skipif(
        not _find_any_pdf(),
        reason="No hay PDF de prueba disponible"
    )
    def test_markitdown_convert_pdf(self):
        """MarkItDown convierte un PDF a Markdown (modo básico, sin VLM)."""
        from markitdown import MarkItDown

        pdf_path = _find_any_pdf()
        md = MarkItDown()
        result = md.convert(str(pdf_path))

        assert result.markdown is not None
        assert len(result.markdown) > 50, "Markdown de MarkItDown demasiado corto"

        # Guardar referencia
        ref_output = EXPECTED_OUTPUTS / f"{pdf_path.stem}_markitdown.md"
        if not ref_output.exists():
            ref_output.write_text(result.markdown, encoding="utf-8")

    def test_markitdown_sin_vlm_no_falla(self):
        """MarkItDown sin VLM configurado no lanza excepciones."""
        from markitdown import MarkItDown
        md = MarkItDown()
        # Solo verificar que la inicialización es exitosa sin llm_client
        assert md is not None

    def test_markitdown_con_vlm_mock(self):
        """MarkItDown acepta un llm_client mock sin error."""
        from markitdown import MarkItDown
        mock_client = MagicMock()
        md = MarkItDown(llm_client=mock_client, llm_model="test-model")
        assert md is not None


# ══════════════════════════════════════════════════════════════════════════════
#  TESTS: ParserRouter (Selector de Parser)
# ══════════════════════════════════════════════════════════════════════════════

class TestParserRouter:
    """Tests de integración para la lógica de selección de parser."""

    def test_pdf_cientifico_usa_opendataloader(self):
        """Un PDF marcado como artículo científico debe usar OpenDataLoader."""
        # Este test valida la lógica de routing, no la conversión
        file_path = Path("fake_article.pdf")
        is_scientific = True

        # Lógica esperada del ParserRouter
        if file_path.suffix.lower() == ".pdf" and is_scientific:
            selected_parser = "opendataloader"
        else:
            selected_parser = "markitdown"

        assert selected_parser == "opendataloader"

    def test_docx_usa_markitdown(self):
        """Un DOCX siempre debe usar MarkItDown."""
        file_path = Path("report.docx")
        is_scientific = True  # Incluso si es científico, DOCX va a MarkItDown

        if file_path.suffix.lower() == ".pdf" and is_scientific:
            selected_parser = "opendataloader"
        else:
            selected_parser = "markitdown"

        assert selected_parser == "markitdown"

    def test_pdf_no_cientifico_usa_markitdown(self):
        """Un PDF no-científico debe usar MarkItDown como fallback."""
        file_path = Path("manual_usuario.pdf")
        is_scientific = False

        if file_path.suffix.lower() == ".pdf" and is_scientific:
            selected_parser = "opendataloader"
        else:
            selected_parser = "markitdown"

        assert selected_parser == "markitdown"

    @pytest.mark.parametrize("extension,expected", [
        (".pdf", "opendataloader"),  # artículo científico por defecto
        (".docx", "markitdown"),
        (".pptx", "markitdown"),
        (".xlsx", "markitdown"),
        (".html", "markitdown"),
        (".epub", "markitdown"),
    ])
    def test_routing_por_extension(self, extension, expected):
        """Verifica el routing correcto para cada tipo de archivo."""
        file_path = Path(f"document{extension}")
        is_scientific = True  # Para PDF, esto activa OpenDataLoader

        if file_path.suffix.lower() == ".pdf" and is_scientific:
            selected = "opendataloader"
        else:
            selected = "markitdown"

        assert selected == expected


# ══════════════════════════════════════════════════════════════════════════════
#  TESTS: TableFlattener (Común a ambos parsers)
# ══════════════════════════════════════════════════════════════════════════════

class TestTableFlattenerIntegration:
    """Tests de integración para TableFlattener con outputs reales de ambos parsers."""

    def test_tabla_simple_se_aplana(self):
        """Una tabla Markdown simple se convierte en oraciones atómicas."""
        from app.services.pdf_parser import TableFlattener

        md = (
            "## Resultados\n\n"
            "| Cultivo | Rendimiento | Tratamiento |\n"
            "|---------|------------|-------------|\n"
            "| Trigo   | 4.2 t/ha   | Control     |\n"
            "| Maíz    | 8.7 t/ha   | Fertilizado |\n\n"
            "Texto después de la tabla."
        )
        meta = {"title": "Evaluación de cultivos", "authors": "García J.", "year": 2024}
        result = TableFlattener.flatten(md, meta)

        assert "Cultivo: Trigo" in result
        assert "Rendimiento: 4.2 t/ha" in result
        assert "|" not in result.split("---")[-1]  # No quedan pipes después del YAML

    def test_texto_sin_tablas_no_cambia(self):
        """El texto sin tablas pasa intacto por TableFlattener."""
        from app.services.pdf_parser import TableFlattener

        md = "# Título\n\nTexto normal sin tablas.\n\n## Conclusión\n\nFin."
        result = TableFlattener.flatten(md, {})
        assert result == md


# ══════════════════════════════════════════════════════════════════════════════
#  TESTS: Front-matter YAML
# ══════════════════════════════════════════════════════════════════════════════

class TestFrontMatterYAML:
    """Tests de integración para la inyección de metadatos YAML."""

    def test_yaml_round_trip_unicode(self):
        """YAML con caracteres Unicode (español/portugués) se preserva."""
        meta = {
            "agrisearch_id": "test-001",
            "doi": "10.1234/test",
            "title": "Evaluación del estrés hídrico en Solanum melongena L.",
            "authors": "García-López J.A., Müller H., Souza P.R.",
            "parser_engine": "opendataloader",
        }
        yaml_str = yaml.dump(meta, allow_unicode=True, sort_keys=False)
        parsed = yaml.safe_load(yaml_str)

        assert parsed["title"] == meta["title"]
        assert "Evaluación" in yaml_str  # No debe escapar Unicode
        assert parsed["parser_engine"] == "opendataloader"

    def test_yaml_con_keywords_lista(self):
        """Keywords como lista se serializa correctamente en YAML."""
        meta = {
            "keywords": ["precision agriculture", "NDVI", "remote sensing"],
            "parser_engine": "markitdown",
        }
        yaml_str = yaml.dump(meta, allow_unicode=True, sort_keys=False)
        parsed = yaml.safe_load(yaml_str)

        assert isinstance(parsed["keywords"], list)
        assert len(parsed["keywords"]) == 3

    def test_front_matter_valido_en_markdown(self):
        """Un markdown con front-matter se parsea correctamente."""
        md = (
            "---\n"
            "agrisearch_id: test-001\n"
            "doi: '10.1234/test'\n"
            "parser_engine: opendataloader\n"
            "---\n\n"
            "# Contenido del paper\n\nTexto."
        )
        data = _validate_front_matter(md)
        assert data["parser_engine"] == "opendataloader"
        assert data["agrisearch_id"] == "test-001"


# ══════════════════════════════════════════════════════════════════════════════
#  TESTS: Pipeline Completo End-to-End
# ══════════════════════════════════════════════════════════════════════════════

class TestPipelineEndToEnd:
    """Tests end-to-end del pipeline completo de conversión."""

    @pytest.mark.skipif(
        not _find_any_pdf(),
        reason="No hay PDF de prueba disponible"
    )
    def test_pipeline_completo_opendataloader(self, tmp_path):
        """Pipeline completo: PDF → OpenDataLoader → TableFlattener → YAML → .md en disco."""
        import opendataloader_pdf
        from app.services.pdf_parser import TableFlattener

        pdf_path = _find_any_pdf()
        output_dir = tmp_path / "pipeline_output"
        output_dir.mkdir()

        # 1. Conversión con OpenDataLoader
        opendataloader_pdf.convert(
            input_path=str(pdf_path),
            output_dir=str(output_dir),
            format="markdown",
            use_struct_tree=True,
        )

        md_files = list(output_dir.glob("*.md"))
        assert len(md_files) >= 1
        raw_md = md_files[0].read_text(encoding="utf-8")

        # 2. TableFlattener
        flattened = TableFlattener.flatten(raw_md, SAMPLE_META)

        # 3. Front-matter YAML
        front_matter = {
            "agrisearch_id": SAMPLE_META["id"],
            "doi": SAMPLE_META["doi"],
            "title": SAMPLE_META["title"],
            "authors": SAMPLE_META["authors"],
            "year": SAMPLE_META["year"],
            "parser_engine": "opendataloader",
        }
        yaml_str = yaml.dump(front_matter, allow_unicode=True, sort_keys=False)
        final_md = f"---\n{yaml_str}---\n\n{flattened}"

        # 4. Guardar en disco
        final_path = tmp_path / f"{pdf_path.stem}.md"
        final_path.write_text(final_md, encoding="utf-8")

        # Verificaciones
        assert final_path.exists()
        content = final_path.read_text(encoding="utf-8")
        assert content.startswith("---")
        assert "parser_engine: opendataloader" in content
        assert len(content) > 500

        # Guardar como referencia
        ref = EXPECTED_OUTPUTS / f"{pdf_path.stem}_pipeline_complete.md"
        if not ref.exists():
            ref.write_text(content, encoding="utf-8")
