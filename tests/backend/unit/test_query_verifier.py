"""
Archivo: test_query_verifier.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Suite de pruebas unitarias para el componente `QueryVerifier`. Asegura la 
correcta detección y categorización de diagnósticos de búsqueda, verificando 
que se generen los prefijos adecuados (`[ALERTA]`, `[WARNING]`, `[ERROR]`, `[SLOW]`) 
según los umbrales de resultados y tiempos de respuesta.

Acciones Principales:
    - Validación de alertas por cero resultados.
    - Validación de advertencias por baja densidad de resultados (umbral < 3).
    - Verificación de reporte de errores críticos.
    - Detección de tiempos de respuesta lentos (umbral > 15s).
    - Comprobación de priorización de errores sobre otras alertas.

Estructura Interna:
    - `TestQueryVerifier`: Clase con métodos de prueba para diferentes escenarios.

Entradas / Dependencias:
    - `app.services.query_verifier`.
    - `pytest`.

Salidas / Efectos:
    - Verificación lógica del motor de diagnósticos.
    - Generación de reportes de cumplimiento de reglas de validación en consola.

Ejecución:
    pytest tests/backend/unit/test_query_verifier.py
"""

import pytest
from app.services.query_verifier import QueryDiagnostic, QueryVerifier


class TestQueryVerifier:
    """Tests de QueryVerifier.verify()."""

    def test_zero_results_alerts(self):
        """0 resultados genera [ALERTA]."""
        diag = QueryDiagnostic(
            database="openalex",
            query_sent="test query",
            results_count=0,
        )
        alerts = QueryVerifier.verify(diag)
        assert len(alerts) == 1
        assert "[ALERTA]" in alerts[0]
        assert "openalex" in alerts[0]
        assert "0 resultados" in alerts[0]

    def test_few_results_warns(self):
        """2 resultados genera [WARNING]."""
        diag = QueryDiagnostic(
            database="arxiv",
            query_sent="test query",
            results_count=2,
        )
        alerts = QueryVerifier.verify(diag)
        assert len(alerts) == 1
        assert "[WARNING]" in alerts[0]
        assert "2 resultados" in alerts[0]

    def test_error_alerts(self):
        """Error genera [ERROR]."""
        diag = QueryDiagnostic(
            database="crossref",
            query_sent="test query",
            error="Connection timeout",
        )
        alerts = QueryVerifier.verify(diag)
        assert len(alerts) == 1
        assert "[ERROR]" in alerts[0]
        assert "crossref" in alerts[0]
        assert "Connection timeout" in alerts[0]

    def test_slow_response_alerts(self):
        """Tiempo >15s genera [SLOW]."""
        diag = QueryDiagnostic(
            database="agecon",
            query_sent="test query",
            results_count=5,
            response_time_ms=20000,
        )
        alerts = QueryVerifier.verify(diag)
        assert len(alerts) == 1
        assert "[SLOW]" in alerts[0]
        assert "20000ms" in alerts[0]

    def test_good_results_no_alerts(self):
        """3+ resultados sin error ni slow no genera alertas."""
        diag = QueryDiagnostic(
            database="scielo",
            query_sent="test query",
            results_count=10,
            response_time_ms=5000,
        )
        alerts = QueryVerifier.verify(diag)
        assert len(alerts) == 0

    def test_error_blocks_other_alerts(self):
        """Error retorna solo [ERROR], no otros alertas."""
        diag = QueryDiagnostic(
            database="core",
            query_sent="test query",
            results_count=0,
            error="401 Unauthorized",
            response_time_ms=20000,
        )
        alerts = QueryVerifier.verify(diag)
        assert len(alerts) == 1
        assert "[ERROR]" in alerts[0]

    def test_multiple_alerts(self):
        """Pocos resultados + slow genera 2 alertas."""
        diag = QueryDiagnostic(
            database="redalyc",
            query_sent="test query",
            results_count=1,
            response_time_ms=18000,
        )
        alerts = QueryVerifier.verify(diag)
        assert len(alerts) == 2
        assert any("[WARNING]" in a for a in alerts)
        assert any("[SLOW]" in a for a in alerts)

    def test_exactly_min_results_no_warning(self):
        """Exactamente MIN_RESULTS_WARNING (3) no genera warning."""
        diag = QueryDiagnostic(
            database="openalex",
            query_sent="test query",
            results_count=3,
        )
        alerts = QueryVerifier.verify(diag)
        assert len(alerts) == 0
