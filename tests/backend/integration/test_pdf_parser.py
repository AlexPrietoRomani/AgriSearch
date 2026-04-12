import pytest
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.pdf_parser import pdf_parser, TableFlattener
from app.models.project import Article
from app.core.config import get_settings

@pytest.mark.asyncio
async def test_table_flattener_basic():
    """Test the TableFlattener logic with a sample markdown table."""
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
    """Test parsing a real PDF from the data directory (if it exists)."""
    # Use a known existing file for integration testing
    sample_pdf = Path("data/projects/75e9f074-593d-4c64-a9f8-71691ae1bb70/pdfs/Alreshidi_2019.pdf")
    
    if not sample_pdf.exists():
        pytest.skip(f"Sample PDF not found at {sample_pdf}")

    # Create dummy article
    article = Article(
        id="test-article-id",
        project_id="75e9f074-593d-4c64-a9f8-71691ae1bb70",
        title="Alreshidi 2019 Study",
        authors="Alreshidi et al.",
        year=2019,
        local_pdf_path=str(sample_pdf),
        source_database="arxiv"
    )
    
    # We need a synchronous session for the service for now, or adapt the service
    # Our service uses 'db: Session' (sync).
    # Since we use aiosqlite, we need to be careful.
    
    # Let's mock the db.commit() to avoid dependency on real DB for this logic test
    from unittest.mock import MagicMock
    mock_db = MagicMock()

    success = await pdf_parser.parse_article(article, mock_db)
    
    assert success is True
    assert article.parsed_status == "success"
    assert article.local_md_path is not None
    assert os.path.exists(article.local_md_path)
    
    # Check content
    with open(article.local_md_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "---" in content
        assert "agrisearch_id: test-article-id" in content
        assert "title: Alreshidi 2019 Study" in content
        # Check if some text from the PDF is there (very basic check)
        assert len(content) > 100
