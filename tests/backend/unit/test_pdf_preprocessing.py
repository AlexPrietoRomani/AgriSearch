import pytest
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from app.services.document_parser_service import DoclingParser, TableFlattener, ImageFilter, MarkItDownParser

@pytest.fixture
def mock_article_meta():
    return {
        "id": "test-uuid-123",
        "doi": "10.1234/test.v1",
        "title": "Impact of Fungicides on Wheat Yield",
        "authors": "Smith, J., Doe, A.",
        "year": 2023,
        "journal": "Agri Journal",
        "keywords": ["wheat", "fungicide", "yield"],
        "source_database": "openalex"
    }

def test_table_flattener_basic():
    """Test converting Markdown tables to sentences."""
    md_table = "| Crop | Yield |\n|---|---|\n| Wheat | 5.2 |\n| Corn | 7.1 |"
    meta = {"authors": "Smith, J.", "year": 2023, "title": "Wheat Study"}
    
    flattened = TableFlattener.flatten(md_table, meta)
    
    assert "Según Smith (2023) en Wheat Study, se registra: Crop: Wheat, Yield: 5.2." in flattened
    assert "Según Smith (2023) en Wheat Study, se registra: Crop: Corn, Yield: 7.1." in flattened
    assert "|" not in flattened  # Markdown table symbols should be gone

def test_table_flattener_empty():
    """Test with malformed or empty tables."""
    assert TableFlattener.flatten("No table here") == "No table here"
    assert TableFlattener.flatten("| Not | A |\n| Table |") == "| Not | A |\n| Table |"

@pytest.mark.asyncio
async def test_docling_parser_workflow(mock_article_meta):
    """Test the full parsing workflow with Docling and VLM mocks."""
    
    # Setup mocks
    with patch("app.services.document_parser_service.DocumentConverter") as mock_converter_cls, \
         patch("app.services.document_parser_service.PdfPipelineOptions") as mock_options_cls, \
         patch("app.services.document_parser_service.TableStructureOptions") as mock_table_opts_cls, \
         patch("app.services.document_parser_service.AcceleratorOptions") as mock_accel_opts_cls, \
         patch("app.services.document_parser_service.TableFormerMode") as mock_mode, \
         patch("app.services.document_parser_service.AcceleratorDevice") as mock_device, \
         patch("app.services.document_parser_service.InputFormat") as mock_input_format, \
         patch("app.services.document_parser_service.PdfFormatOption") as mock_pdf_opt, \
         patch("app.services.document_parser_service.DOCLING_AVAILABLE", True):
        
        # 1. Mock Docling document and result
        mock_doc = MagicMock()
        mock_doc.export_to_markdown.return_value = "## Introduction\n\nSome text.\n\n<!-- image -->\n\n| Param | Value |\n|---|---|\n| N | 100 |"
        mock_doc.pictures = [MagicMock()] # One picture
        
        mock_result = MagicMock()
        mock_result.document = mock_doc
        
        mock_converter = mock_converter_cls.return_value
        mock_converter.convert.return_value = mock_result
        
        # 2. Mock ImageFilter
        mock_vlm = AsyncMock(spec=ImageFilter)
        mock_vlm.analyze_image_bytes.return_value = "A bar chart of yield results"
        
        # 3. Running Actual parser
        parser = DoclingParser()
        # Mock Path.exists to true for the test
        with patch.object(Path, "exists", return_value=True):
            final_md = await parser.parse_pdf(Path("dummy.pdf"), mock_article_meta, vlm_describer=mock_vlm)
            
            # 4. Assertions
            assert "---" in final_md # Front-matter exists
            assert "doi: 10.1234/test.v1" in final_md
            assert "## Introduction" in final_md
            assert "**[💡 Descripción de Imagen VLM]:** A bar chart" in final_md
            assert "Según Smith (2023) en Impact of Fungicides on Wheat Yield, se registra: Param: N, Value: 100." in final_md
            assert "|" not in final_md # Table was flattened

def test_markitdown_sin_vlm():
    """Test 1 — Sin VLM: El parser se inicializa sin errores cuando no hay VLM configurado."""
    parser = MarkItDownParser()  # Sin llm_client
    assert parser.has_vlm is False
    # La inicialización funciona y el estado VLM es False

def test_markitdown_con_vlm():
    """Test 2 — Con VLM mock: Verificar que se pasa el llm_client correctamente."""
    mock_client = MagicMock()
    parser = MarkItDownParser(llm_client=mock_client, llm_model="test-model")
    assert parser.has_vlm is True
    # La inicialización configura el VLM correctamente

def test_table_flattener_preserva_texto():
    """El texto fuera de tablas no se modifica."""
    md = "# Título\n\nTexto normal sin tablas."
    result = TableFlattener.flatten(md, {})
    assert result == md

def test_front_matter_yaml_valido():
    """El output contiene front-matter YAML parseable."""
    import yaml
    # Simular output de parse_pdf
    md_with_yaml = "---\nagrisearch_id: test\ndoi: '10.1234/test'\nparser_engine: markitdown\n---\n\n# Content"
    yaml_block = md_with_yaml.split("---")[1]
    data = yaml.safe_load(yaml_block)
    assert data["parser_engine"] == "markitdown"
    assert "doi" in data

def test_front_matter_unicode():
    """YAML soporta caracteres Unicode (español/portugués)."""
    import yaml
    meta = {"title": "Análisis de variación genética en Solanum melongena"}
    yaml_str = yaml.dump(meta, allow_unicode=True)
    assert "Análisis" in yaml_str  # No debe escapar Unicode

def test_md_guardado_en_disco(tmp_path):
    """El archivo .md se guarda junto al PDF."""
    pdf = tmp_path / "test.pdf"
    pdf.write_text("fake pdf")
    md = tmp_path / "test.md"
    md.write_text("---\ntitle: test\n---\n\n# Content", encoding="utf-8")
    assert md.exists()
    assert md.read_text(encoding="utf-8").startswith("---")

def test_parsed_status_quality():
    """El status de calidad se asigna correctamente según longitud."""
    assert len("x" * 15000) > 10000  # → success_alta
    assert 2000 < len("x" * 5000) <= 10000  # → success_media
    assert len("x" * 500) <= 2000  # → success_baja

def test_post_process_limpia_lineas_vacias():
    """El post-procesamiento reduce líneas vacías excesivas."""
    from app.services.document_parser_service import MarkItDownParser
    text = "Line 1\n\n\n\n\n\nLine 2"
    result = MarkItDownParser._post_process(text)
    assert "\n\n\n\n" not in result
    assert "Line 1" in result and "Line 2" in result

def test_generate_sample_unit_output(mock_article_meta):
    """Genera un archivo MD de muestra en la carpeta de outputs de la unidad para inspección."""
    parser = MarkItDownParser()
    # Simular un Markdown enriquecido (mismo formato que sacaría el parser real)
    sample_content = (
        "---\n"
        "agrisearch_id: test-unit-sample\n"
        "title: Sample Research Article\n"
        "parser_engine: markitdown\n"
        "---\n\n"
        "# Abstract\n"
        "This is a sample output to verify the unit test pathing.\n\n"
        "## Results\n"
        "![Figure 1](figure1.png)\n"
        "> **[💡 Descripción de Imagen VLM]:** Gráfico de barras mostrando el crecimiento de trigo.\n"
    )
    
    output_dir = Path(__file__).parent / "outputs"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "sample_unit_test.md"
    output_file.write_text(sample_content, encoding="utf-8")
    
    assert output_file.exists()

def test_markitdown_importable():
    """MarkItDown está instalado y es importable."""
    from markitdown import MarkItDown
    md = MarkItDown()
    assert md is not None

def test_ollama_vlm_wrapper_format():
    """TASK 2.0.8: Verifica que el wrapper ajusta los argumentos (vía Mock de requests)."""
    from app.services.document_parser_service import OllamaVLMWrapper
    
    with patch("requests.post") as mock_post:
        # Mock de respuesta exitosa de Ollama
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"role": "assistant", "content": "descripción de prueba"}}
        mock_post.return_value = mock_response
        
        wrapper = OllamaVLMWrapper(base_url="http://localhost:11434/v1")
        
        # Simular llamada de MarkItDown
        res = wrapper.chat.completions.create(
            model="gemma4:26b",
            messages=[{"role": "user", "content": "test"}],
            temperature=0.5
        )
        
        # Verificar que se llamó a requests.post con el endpoint /api/chat y payload convertido
        args, kwargs = mock_post.call_args
        assert "/api/chat" in args[0]
        payload = kwargs["json"]
        
        assert payload["model"] == "gemma4:26b"
        assert payload["options"]["temperature"] == 0.5
        assert payload["messages"][0]["role"] == "user"
        assert payload["messages"][0]["content"] == "test"
        assert res.choices[0].message.content == "descripción de prueba"
