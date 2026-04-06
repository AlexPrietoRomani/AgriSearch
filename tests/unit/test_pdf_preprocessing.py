import pytest
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from app.services.document_parser_service import DoclingParser, TableFlattener, ImageFilter

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
