import sys
import os
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from app.services.download_service import download_articles, _sanitize_filename
from app.models.project import Article, DownloadStatus

@pytest.fixture
def mock_db_session():
    """Mock an AsyncSession for testing db calls."""
    session = AsyncMock()
    # Ensure db.execute returns a result with scalars().all() -> list of articles
    return session


@pytest.mark.asyncio
async def test_download_articles_with_specific_ids(mock_db_session):
    """Test downloading specifically requested article IDs."""

    # Mock article
    mock_article = Article(
        id="test-article-1",
        project_id="test-project",
        title="Test Article Title",
        authors="Smith, J., Doe, A.",
        year=2024,
        open_access_url="https://example.com/test.pdf",
        download_status=DownloadStatus.PENDING,
        is_duplicate=False
    )
    
    # Mock DB execute result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_article]
    mock_db_session.execute.return_value = mock_result

    # Mock settings to return a temp directory
    with patch("app.services.download_service.settings") as mock_settings:
        mock_settings.get_project_pdfs_dir.return_value = Path("/tmp/mock_pdfs")
        mock_settings.download_rate_limit = 5
        mock_settings.download_timeout = 30
        
        # Mock aiohttp
        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            # Magic bytes for PDF
            mock_resp.read = AsyncMock(return_value=b"%PDF-1.4 mock content")
            
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            
            mock_session = AsyncMock()
            mock_session.get = MagicMock(return_value=mock_ctx)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            
            mock_session_cls.return_value = mock_session
            
            # Patch pathlib.Path.write_bytes and exists to simulate download
            with patch.object(Path, "exists", return_value=False), \
                 patch.object(Path, "write_bytes") as mock_write:
                 
                results = await download_articles(
                    db=mock_db_session, 
                    project_id="test-project", 
                    article_ids=["test-article-1"]
                )
                
                # Check results
                assert results["total"] == 1
                assert results["downloaded"] == 1
                assert results["failed"] == 0
                
                # Check that DB flush was called
                mock_db_session.flush.assert_called_once()
                
                # Verify that the article status and local_pdf_path were updated
                assert mock_article.download_status == DownloadStatus.SUCCESS.value
                assert "2024" in mock_article.local_pdf_path
                assert "Smith" in mock_article.local_pdf_path


@pytest.mark.asyncio
async def test_download_articles_pdf_validation_failure(mock_db_session):
    """Test downloading when the returned content is not a PDF."""

    mock_article = Article(
        id="test-article-2",
        project_id="test-project",
        title="HTML Article",
        open_access_url="https://example.com/test.html",
        download_status=DownloadStatus.PENDING,
        is_duplicate=False
    )
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_article]
    mock_db_session.execute.return_value = mock_result

    with patch("app.services.download_service.settings") as mock_settings:
        mock_settings.get_project_pdfs_dir.return_value = Path("/tmp/mock_pdfs")
        mock_settings.download_rate_limit = 5
        
        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            # Not PDF magic bytes
            mock_resp.read = AsyncMock(return_value=b"<!DOCTYPE html> content")
            
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            
            mock_session = AsyncMock()
            mock_session.get = MagicMock(return_value=mock_ctx)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            
            mock_session_cls.return_value = mock_session
            
            with patch.object(Path, "exists", return_value=False):
                results = await download_articles(
                    db=mock_db_session, 
                    project_id="test-project", 
                    article_ids=["test-article-2"]
                )
                
                assert results["total"] == 1
                assert results["failed"] == 1
                assert results["downloaded"] == 0
                
                # Verify the article status
                assert mock_article.download_status == DownloadStatus.FAILED.value


def test_sanitize_filename():
    """Test filename sanitization utility."""
    assert _sanitize_filename("Valid Name 123") == "Valid_Name_123"
    assert _sanitize_filename("Invalid/Name\\With|Bad<Chars>") == "Invalid_Name_With_Bad_Chars_"
    assert len(_sanitize_filename("A" * 200)) == 100
