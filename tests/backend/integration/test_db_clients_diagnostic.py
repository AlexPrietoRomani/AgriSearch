"""
Archivo: test_db_clients_diagnostic.py
Modificación: 2026-05-14
Autor: Antigravity

Descripción:
Herramienta de diagnóstico integral para validar la salud de todas las integraciones
bibliográficas. Ejecuta búsquedas reales en cada API configurada (OpenAlex, 
ArXiv, SciELO, Semantic Scholar, Crossref, AgEcon, Organic Eprints).

Sustentación Técnica:
Este script utiliza los adaptadores de query específicos de cada motor para
garantizar que los cambios en la lógica de `query_builder` funcionen en producción.

Acciones Principales:
    - Generar queries adaptadas para cada base de datos.
    - Ejecutar llamadas asíncronas concurrentes a cada cliente.
    - Reportar estadísticas de resultados, títulos de ejemplo y metadatos (DOI, Tipo).

Estructura Interna:
    - `run_test`: Orquestador de ejecución individual con manejo de excepciones.
    - `main`: Punto de entrada que define la consulta maestra y coordina el reporte.

Ejecución:
    uv run python tests/backend/integration/test_db_clients_diagnostic.py
"""

import asyncio
import logging
import sys
import os

# Asegura que el path incluya la raíz del proyecto para importar 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../backend")))

logging.basicConfig(level=logging.WARNING, format="%(name)s | %(levelname)s | %(message)s")
logger = logging.getLogger("diagnostic")

# --- Parámetros de la prueba ---------------------------------------------------
QUERY_CONCEPTS = ["Vision Transformer", "CNN", "agriculture", "phenology"]
QUERY_SYNONYMS = {
    "Vision Transformer": ["ViT"],
    "CNN": ["Convolutional Neural Network"],
    "agriculture": ["precision agriculture"],
    "phenology": ["phenological stage", "phenology detection"],
}
YEAR_FROM = 2020
YEAR_TO = 2026
MAX_RESULTS = 10 


async def run_test(name: str, coro) -> None:
    """
    Ejecuta una corrutina de búsqueda y reporta el estado en consola.

    Args:
        name (str): Nombre amigable de la base de datos.
        coro: Corrutina del cliente de búsqueda.
    """
    print(f"\n{'='*60}")
    print(f"  DIAGNÓSTICO: {name}")
    print(f"{'='*60}")
    try:
        results = await coro
        if results:
            print(f"  [OK] {len(results)} resultados obtenidos")
            first = results[0]
            print(f"       Ejemplo: {first.get('title', 'N/A')[:70]}...")
            print(f"       Metadatos -> Año: {first.get('year', 'N/A')}, DOI: {first.get('doi', 'N/A')}, Tipo: {first.get('document_type', 'N/A')}")
        else:
            print("  [WARN] 0 resultados. Verificar query o estado de la API.")
    except Exception as exc:
        print(f"  [ERROR] {type(exc).__name__}: {exc}")


async def main() -> None:
    """Orquesta el diagnóstico de todos los clientes configurados."""
    from app.services.query_builder import (
        build_arxiv_query,
        build_semantic_scholar_query,
        build_openalex_query,
        build_scielo_query,
        build_oaipmh_query,
        build_crossref_query,
    )
    from app.services.mcp_clients.openalex_client import search_openalex
    from app.services.mcp_clients.semantic_scholar_client import search_semantic_scholar
    from app.services.mcp_clients.arxiv_client import search_arxiv
    from app.services.mcp_clients.crossref_client import search_crossref
    from app.services.mcp_clients.scielo_client import search_scielo
    from app.services.mcp_clients.oaipmh_client import search_oaipmh

    print("\n" + "!"*60)
    print("  INICIANDO DIAGNÓSTICO INTEGRAL DE CLIENTES BIBLIOGRÁFICOS")
    print("!"*60)

    # Generación de queries adaptadas
    queries = {
        "openalex": build_openalex_query(QUERY_CONCEPTS, QUERY_SYNONYMS),
        "semantic_scholar": build_semantic_scholar_query(QUERY_CONCEPTS, QUERY_SYNONYMS),
        "arxiv": build_arxiv_query(QUERY_CONCEPTS, QUERY_SYNONYMS),
        "crossref": build_crossref_query(QUERY_CONCEPTS, QUERY_SYNONYMS),
        "scielo": build_scielo_query(QUERY_CONCEPTS, QUERY_SYNONYMS),
        "agecon": build_oaipmh_query(QUERY_CONCEPTS, QUERY_SYNONYMS),
        "organic_eprints": build_oaipmh_query(QUERY_CONCEPTS, QUERY_SYNONYMS),
    }

    # Ejecución de pruebas
    tasks = [
        run_test("OpenAlex", search_openalex(queries["openalex"], MAX_RESULTS, YEAR_FROM, YEAR_TO)),
        run_test("Semantic Scholar", search_semantic_scholar(queries["semantic_scholar"], MAX_RESULTS, YEAR_FROM, YEAR_TO)),
        run_test("ArXiv", search_arxiv(queries["arxiv"], MAX_RESULTS, YEAR_FROM, YEAR_TO)),
        run_test("Crossref", search_crossref(queries["crossref"], MAX_RESULTS, YEAR_FROM, YEAR_TO)),
        run_test("SciELO", search_scielo(queries["scielo"], MAX_RESULTS, YEAR_FROM, YEAR_TO)),
        run_test("AgEcon", search_oaipmh(queries["agecon"], "agecon", MAX_RESULTS, YEAR_FROM, YEAR_TO)),
        run_test("Organic Eprints", search_oaipmh(queries["organic_eprints"], "organic_eprints", MAX_RESULTS, YEAR_FROM, YEAR_TO)),
    ]
    
    await asyncio.gather(*tasks)

    print("\n" + "="*60)
    print("  DIAGNÓSTICO FINALIZADO")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
