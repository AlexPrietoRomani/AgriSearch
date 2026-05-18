"""
Tests para TASK 4.7.2: BackgroundTask + SSE para construcción de grafos.

Cubre:
- POST /build retorna 202 Accepted inmediatamente
- Background task ejecuta pipeline completo
- Eventos SSE publicados correctamente
- Status endpoint funciona
- Auto-fallback a screening_status="all" cuando no hay decisiones
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path


class TestBuildEndpointReturns202:
    """POST /build debe retornar 202 Accepted inmediatamente."""

    @pytest.mark.asyncio
    async def test_build_returns_accepted(self):
        """Endpoint retorna 202 con build_id."""
        from app.api.v1.graphs import build_graphs, BuildGraphRequest
        from fastapi import BackgroundTasks
        
        mock_bg = MagicMock(spec=BackgroundTasks)
        mock_db = AsyncMock()
        
        response = await build_graphs(
            project_id="proj-001",
            background_tasks=mock_bg,
            request=BuildGraphRequest(screening_status="included"),
            db=mock_db,
        )
        
        assert response["status"] == "accepted"
        assert "build_id" in response
        assert "progress_endpoint" in response
        assert mock_bg.add_task.called

    @pytest.mark.asyncio
    async def test_build_invalid_screening_status(self):
        """Screening status inválido retorna 400."""
        from app.api.v1.graphs import build_graphs, BuildGraphRequest
        from fastapi import BackgroundTasks, HTTPException
        
        mock_bg = MagicMock(spec=BackgroundTasks)
        mock_db = AsyncMock()
        
        with pytest.raises(HTTPException) as exc:
            await build_graphs(
                project_id="proj-001",
                background_tasks=mock_bg,
                request=BuildGraphRequest(screening_status="invalid"),
                db=mock_db,
            )
        
        assert exc.value.status_code == 400


class TestBackgroundTaskPipeline:
    """Background task ejecuta pipeline completo y publica eventos SSE."""

    @pytest.mark.asyncio
    async def test_background_task_publishes_progress_events(self):
        """Task publica eventos graph_build_progress, success/error."""
        from app.api.v1.graphs import _build_graphs_background
        from app.api.v1.events import publish_event
        
        published_events = []
        
        async def mock_publish(project_id, message):
            published_events.append(message)
        
        mock_article = MagicMock()
        mock_article.id = "art-001"
        mock_article.doi = "10.1234/test"
        mock_article.title = "Test Article"
        mock_article.abstract = "Test abstract"
        mock_article.local_md_path = "/tmp/test.md"
        
        with patch("app.api.v1.graphs.publish_event", side_effect=mock_publish):
            with patch("app.api.v1.graphs.build_reference_batch_from_md", new_callable=AsyncMock) as mock_ref:
                mock_ref.return_value = {
                    "total_articles": 1,
                    "articles_with_md": 1,
                    "total_references_extracted": 5,
                    "references_in_project": 2,
                    "references_external": 3,
                    "errors": 0,
                }
                with patch("app.api.v1.graphs.CitationGraphBuilder") as mock_citation:
                    mock_builder = MagicMock()
                    mock_builder.build_directed_graph = AsyncMock()
                    mock_builder.save_graph.return_value = Path("/tmp/citation.json")
                    mock_builder.calculate_metrics.return_value = {"nodes": 10, "edges": 15}
                    mock_citation.return_value = mock_builder
                    
                    with patch("app.api.v1.graphs.ThematicGraphBuilder") as mock_thematic:
                        mock_t_builder = MagicMock()
                        mock_t_builder.get_or_generate_embeddings = AsyncMock(return_value=([], []))
                        mock_t_builder.serialize_and_save.return_value = {"metadata": {"nodes": 8}}
                        mock_thematic.return_value = mock_t_builder
                        
                        with patch("app.api.v1.graphs.get_eligible_articles_for_graphs", new_callable=AsyncMock) as mock_eligible:
                            mock_eligible.return_value = [mock_article]
                            
                            with patch("app.api.v1.graphs.async_session_factory") as mock_session:
                                mock_ctx = AsyncMock()
                                mock_ctx.__aenter__.return_value = mock_ctx
                                mock_session.return_value = mock_ctx
                                
                                await _build_graphs_background("proj-001", "included")
        
        event_types = [e.get("type") for e in published_events]
        
        assert "graph_build_progress" in event_types
        assert "graph_build_success" in event_types

    @pytest.mark.asyncio
    async def test_background_task_publishes_error_on_failure(self):
        """Task publica graph_build_error cuando falla."""
        from app.api.v1.graphs import _build_graphs_background
        
        published_events = []
        
        async def mock_publish(project_id, message):
            published_events.append(message)
        
        with patch("app.api.v1.graphs.publish_event", side_effect=mock_publish):
            with patch("app.api.v1.graphs.build_reference_batch_from_md", new_callable=AsyncMock) as mock_ref:
                mock_ref.side_effect = Exception("DB connection failed")
                
                with patch("app.api.v1.graphs.async_session_factory") as mock_session:
                    mock_ctx = AsyncMock()
                    mock_ctx.__aenter__.return_value = mock_ctx
                    mock_session.return_value = mock_ctx
                    
                    await _build_graphs_background("proj-001", "included")
        
        event_types = [e.get("type") for e in published_events]
        
        assert "graph_build_error" in event_types
        error_event = [e for e in published_events if e.get("type") == "graph_build_error"][0]
        assert "DB connection failed" in error_event.get("message", "")


class TestBuildStatusEndpoint:
    """GET /build/{build_id}/status retorna estado actual."""

    @pytest.mark.asyncio
    async def test_status_endpoint_returns_current_status(self):
        """Status endpoint retorna estado del build."""
        from app.api.v1.graphs import get_build_status_endpoint, set_build_status
        
        set_build_status("proj-001", {
            "build_id": "abc123",
            "status": "running",
            "progress": 50,
            "step": "building_citation_graph",
        })
        
        response = await get_build_status_endpoint("proj-001", "abc123")
        
        assert response["status"] == "running"
        assert response["progress"] == 50

    @pytest.mark.asyncio
    async def test_status_endpoint_404_no_build(self):
        """Status endpoint retorna 404 si no hay build."""
        from app.api.v1.graphs import get_build_status_endpoint
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc:
            await get_build_status_endpoint("proj-nonexistent", "xyz789")
        
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_status_endpoint_build_id_mismatch(self):
        """Status endpoint retorna mismatch si build_id no coincide."""
        from app.api.v1.graphs import get_build_status_endpoint, set_build_status
        
        set_build_status("proj-001", {
            "build_id": "abc123",
            "status": "running",
        })
        
        response = await get_build_status_endpoint("proj-001", "wrong-id")
        
        assert response["status"] == "mismatch"


class TestBuildStatusTracker:
    """In-memory build status tracker."""

    def test_set_and_get_build_status(self):
        """Status tracker almacena y recupera estados."""
        from app.api.v1.graphs import set_build_status, get_build_status
        
        set_build_status("proj-001", {"status": "running", "progress": 0})
        
        status = get_build_status("proj-001")
        
        assert status is not None
        assert status["status"] == "running"

    def test_get_build_status_returns_none_for_unknown(self):
        """Status retorna None para proyecto desconocido."""
        from app.api.v1.graphs import get_build_status
        
        assert get_build_status("nonexistent") is None


class TestAutoFallback:
    """Auto-fallback a screening_status='all' cuando no hay decisiones."""

    @pytest.mark.asyncio
    async def test_build_fallbacks_to_all_when_no_decisions(self):
        """Endpoint aplica fallback a 'all' si no hay screening decisions."""
        from app.api.v1.graphs import build_graphs, BuildGraphRequest
        from fastapi import BackgroundTasks
        
        mock_bg = MagicMock(spec=BackgroundTasks)
        mock_db = AsyncMock()
        
        with patch("app.api.v1.graphs.has_screening_decisions", new_callable=AsyncMock) as mock_has:
            mock_has.return_value = False
            
            response = await build_graphs(
                project_id="proj-001",
                background_tasks=mock_bg,
                request=BuildGraphRequest(screening_status="included"),
                db=mock_db,
            )
            
            assert response["status"] == "accepted"
            assert response["screening_status"] == "all"
            assert response["applied_fallback"] is True

    @pytest.mark.asyncio
    async def test_build_keeps_requested_status_when_decisions_exist(self):
        """Endpoint mantiene status solicitado si hay screening decisions."""
        from app.api.v1.graphs import build_graphs, BuildGraphRequest
        from fastapi import BackgroundTasks
        
        mock_bg = MagicMock(spec=BackgroundTasks)
        mock_db = AsyncMock()
        
        with patch("app.api.v1.graphs.has_screening_decisions", new_callable=AsyncMock) as mock_has:
            mock_has.return_value = True
            
            response = await build_graphs(
                project_id="proj-001",
                background_tasks=mock_bg,
                request=BuildGraphRequest(screening_status="included"),
                db=mock_db,
            )
            
            assert response["screening_status"] == "included"
            assert response["applied_fallback"] is False

    @pytest.mark.asyncio
    async def test_build_no_fallback_when_all_requested(self):
        """Endpoint no aplica fallback cuando 'all' ya fue solicitado."""
        from app.api.v1.graphs import build_graphs, BuildGraphRequest
        from fastapi import BackgroundTasks
        
        mock_bg = MagicMock(spec=BackgroundTasks)
        mock_db = AsyncMock()
        
        with patch("app.api.v1.graphs.has_screening_decisions", new_callable=AsyncMock) as mock_has:
            response = await build_graphs(
                project_id="proj-001",
                background_tasks=mock_bg,
                request=BuildGraphRequest(screening_status="all"),
                db=mock_db,
            )
            
            assert response["screening_status"] == "all"
            assert response["applied_fallback"] is False
            mock_has.assert_not_called()


class TestHasScreeningDecisions:
    """Tests para has_screening_decisions()."""

    @pytest.mark.asyncio
    async def test_returns_true_when_decisions_exist(self):
        """Retorna True si hay al menos una decisión."""
        from app.services.graph_service import has_screening_decisions
        
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()
        mock_db.execute.return_value = mock_result
        
        result = await has_screening_decisions("proj-001", mock_db)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_no_decisions(self):
        """Retorna False si no hay decisiones."""
        from app.services.graph_service import has_screening_decisions
        
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await has_screening_decisions("proj-001", mock_db)
        
        assert result is False
