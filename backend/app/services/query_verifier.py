"""
Archivo: query_verifier.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Módulo de diagnóstico y verificación de consultas enviadas a bases de datos científicas.
Su propósito es detectar consultas fallidas, vacías o inusualmente lentas para
proporcionar retroalimentación inmediata durante el proceso de búsqueda federada.

Acciones Principales:
    - Análisis de resultados por cada base de datos consultada.
    - Generación de alertas de error, advertencias por pocos resultados y lentitud.
    - Extracción de metadatos de diagnóstico (tiempo de respuesta, conteo).

Estructura Interna:
    - `QueryDiagnostic`: Dataclass para almacenar el estado de una consulta.
    - `QueryVerifier`: Lógica estática para el análisis de diagnósticos.

Entradas / Dependencias:
    - No tiene dependencias externas.

Salidas / Efectos:
    - Retorna una lista de strings con mensajes de alerta formateados (ej. `[ERROR]`, `[SLOW]`).

Ejemplo de Integración:
    from app.services.query_verifier import QueryVerifier, QueryDiagnostic
    diag = QueryDiagnostic(database="arxiv", query_sent="NDVI", results_count=0)
    alerts = QueryVerifier.verify(diag)
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QueryDiagnostic:
    """Diagnóstico de una query enviada a una BD."""
    database: str
    query_sent: str
    results_count: int = 0
    error: Optional[str] = None
    response_time_ms: float = 0.0
    sample_dois: list[str] = field(default_factory=list)


class QueryVerifier:
    """
    Verifica que las consultas enviadas a cada base de datos sean correctas y efectivas.
    """

    MIN_RESULTS_WARNING = 3

    @staticmethod
    def verify(diagnostic: QueryDiagnostic) -> list[str]:
        """
        Analiza un diagnóstico de consulta y genera una lista de alertas si aplica.

        Args:
            diagnostic (QueryDiagnostic): El objeto de diagnóstico con los datos de la ejecución.

        Returns:
            list[str]: Lista de strings con las alertas generadas (vacía si no hay problemas).
        """
        alerts = []

        if diagnostic.error:
            alerts.append(f"[ERROR] {diagnostic.database}: {diagnostic.error}")
            return alerts

        if diagnostic.results_count == 0:
            alerts.append(
                f"[ALERTA] {diagnostic.database}: 0 resultados. "
                f"Query: '{diagnostic.query_sent[:200]}'"
            )
        elif diagnostic.results_count < QueryVerifier.MIN_RESULTS_WARNING:
            alerts.append(
                f"[WARNING] {diagnostic.database}: solo {diagnostic.results_count} resultados"
            )

        if diagnostic.response_time_ms > 15000:
            alerts.append(
                f"[SLOW] {diagnostic.database}: {diagnostic.response_time_ms:.0f}ms"
            )

        return alerts
