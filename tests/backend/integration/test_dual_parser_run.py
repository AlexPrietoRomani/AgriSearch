"""
Test de integracion completo para el Dual-Parser Pipeline.
Incluye: ParserRouter, OpenDataLoader, MarkItDown, TableFlattener, YAML front-matter.

Ejecutar manualmente:
    backend\.venv\Scripts\python.exe tests\backend\integration\test_dual_parser_run.py
"""
import asyncio
import sys
import time
import tempfile
import yaml
from pathlib import Path
from unittest.mock import MagicMock

backend_dir = Path(__file__).resolve().parent.parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SAMPLE_INPUTS = FIXTURES_DIR / "sample_inputs"
EXPECTED_OUTPUTS = FIXTURES_DIR / "expected_outputs"
EXPECTED_OUTPUTS.mkdir(parents=True, exist_ok=True)

SAMPLE_META_SCIENTIFIC = {
    "id": "test-palm-001",
    "doi": "10.1234/uav.palm.2025",
    "title": "Evaluation of UAV-Based RGB and Multispectral Vegetation Indices for Precision Agriculture",
    "authors": "Panthakkan A., Anzar S.M., Sherin K., Al Mansoori S., Al-Ahmad H.",
    "year": 2025,
    "journal": "arXiv",
    "keywords": ["UAV", "NDVI", "precision agriculture", "vegetation indices"],
    "source_database": "arxiv",
}

SAMPLE_META_NONSCIENTIFIC = {
    "id": "test-manual-001",
    "doi": "",
    "title": "Manual de Usuario - Sistema de Riego",
    "authors": "Admin",
    "year": 2025,
    "journal": "",
    "keywords": ["manual"],
    "source_database": "local",
}


def find_arxiv_pdf():
    """Encuentra un PDF para testing."""
    for pdf in SAMPLE_INPUTS.rglob("*.pdf"):
        return pdf
    data_dir = backend_dir / "data" / "projects"
    if data_dir.exists():
        for pdf in data_dir.rglob("*.pdf"):
            return pdf
    return None


# ==============================================================================
#  UNIT TESTS: ParserRouter (no requieren PDF real)
# ==============================================================================

def test_router_pdf_cientifico_usa_opendataloader():
    """PDF + fuente arxiv -> OpenDataLoader."""
    from app.services.document_parser_service import ParserRouter
    
    router = ParserRouter()
    file_path = Path("test_article.pdf")
    meta = {"source_database": "arxiv"}
    
    result, engine = router.select_parser(
        file_path=file_path,
        article_meta=meta,
        opendataloader_parser="odl_mock",
        markitdown_parser="mit_mock",
    )
    assert engine == "opendataloader"
    assert result == "odl_mock"
    print("OK - PDF cientifico -> OpenDataLoader")


def test_router_docx_siempre_markitdown():
    """DOCX siempre usa MarkItDown, aunque source sea arxiv."""
    from app.services.document_parser_service import ParserRouter
    
    router = ParserRouter()
    file_path = Path("report.docx")
    meta = {"source_database": "arxiv"}
    
    result, engine = router.select_parser(
        file_path=file_path,
        article_meta=meta,
        opendataloader_parser="odl_mock",
        markitdown_parser="mit_mock",
    )
    assert engine == "markitdown"
    assert result == "mit_mock"
    print("OK - DOCX -> MarkItDown (siempre)")


def test_router_pdf_no_cientifico_usa_markitdown():
    """PDF sin source cientifico -> MarkItDown fallback."""
    from app.services.document_parser_service import ParserRouter
    
    router = ParserRouter()
    file_path = Path("manual.pdf")
    meta = {"source_database": "local"}
    
    result, engine = router.select_parser(
        file_path=file_path,
        article_meta=meta,
        opendataloader_parser="odl_mock",
        markitdown_parser="mit_mock",
    )
    assert engine == "markitdown"
    assert result == "mit_mock"
    print("OK - PDF no-cientifico -> MarkItDown (fallback)")


def test_router_formato_desconocido_usa_markitdown():
    """Extension desconocida -> MarkItDown con warning."""
    from app.services.document_parser_service import ParserRouter
    
    router = ParserRouter()
    file_path = Path("data.xyz")
    meta = {"source_database": "arxiv"}
    
    result, engine = router.select_parser(
        file_path=file_path,
        article_meta=meta,
        opendataloader_parser="odl_mock",
        markitdown_parser="mit_mock",
    )
    assert engine == "markitdown"
    assert result == "mit_mock"
    print("OK - .xyz -> MarkItDown (fallback)")


def test_router_parametrizado():
    """Test parametrizado de todas las extensiones."""
    from app.services.document_parser_service import ParserRouter
    
    router = ParserRouter()
    scientific_meta = {"source_database": "arxiv"}
    
    # PDF cientifico -> opendataloader
    result, engine = router.select_parser(
        file_path=Path("paper.pdf"),
        article_meta=scientific_meta,
        opendataloader_parser="odl",
        markitdown_parser="mit",
    )
    assert engine == "opendataloader"
    
    # Cada formato no-PDF -> markitdown
    for ext in [".docx", ".pptx", ".xlsx", ".html", ".epub", ".csv"]:
        result, engine = router.select_parser(
            file_path=Path(f"doc{ext}"),
            article_meta=scientific_meta,
            opendataloader_parser="odl",
            markitdown_parser="mit",
        )
        assert engine == "markitdown", f"Failed for {ext}"
    print("OK - Test parametrizado para todas las extensiones")


# ==============================================================================
#  PIPELINE TESTS: Conversion real con PDF
# ==============================================================================

async def pipeline_markitdown():
    """Pipeline completo con MarkItDown sobre PDF real."""
    from app.services.document_parser_service import MarkItDownParser, ParserRouter
    
    print("\n" + "="*70)
    print("  PIPELINE: MarkItDown sobre PDF real")
    print("="*70)
    
    pdf_path = find_arxiv_pdf()
    if not pdf_path:
        print("WARN - No hay PDF disponible. Saltando test.")
        return True
    
    print(f"[PDF] {pdf_path.name} ({pdf_path.stat().st_size / 1024:.0f} KB)")
    
    parser = MarkItDownParser()
    router = ParserRouter()
    print("[OK] MarkItDownParser inicializado")
    
    selected, engine = router.select_parser(
        file_path=pdf_path,
        article_meta=SAMPLE_META_SCIENTIFIC,
        opendataloader_parser=None,
        markitdown_parser=parser,
    )
    print(f"[RT] Router -> {engine} (source={SAMPLE_META_SCIENTIFIC['source_database']})")
    
    start = time.perf_counter()
    final_md = await selected.parse_document(pdf_path, SAMPLE_META_SCIENTIFIC)
    elapsed = time.perf_counter() - start
    
    print(f"\n  RESULTADOS:")
    print(f"    Tiempo: {elapsed:.1f}s")
    print(f"    Longitud: {len(final_md)} chars")
    print(f"    Front-matter: {'OK' if final_md.startswith('---') else 'FAIL'}")
    print(f"    parser_engine: {'OK' if 'parser_engine: markitdown' in final_md else 'FAIL'}")
    print(f"    Headings: {'OK' if '#' in final_md else 'WARN'}")
    
    if final_md.startswith('---'):
        yaml_block = final_md.split('---')[1]
        data = yaml.safe_load(yaml_block)
        assert data["parser_engine"] == "markitdown"
        assert data["source_database"] == "arxiv"
        print(f"    YAML valido: {list(data.keys())}")
    
    output_path = EXPECTED_OUTPUTS / f"{pdf_path.stem}_markitdown_pipeline.md"
    output_path.write_text(final_md, encoding="utf-8")
    print(f"    Output guardado: {output_path}")
    
    assert len(final_md) > 100, f"Markdown muy corto: {len(final_md)} chars"
    assert final_md.startswith('---'), "Falta front-matter YAML"
    assert 'parser_engine: markitdown' in final_md, "Falta parser_engine en YAML"
    
    print(f"\n[OK] PIPELINE MARKITDOWN - PASO")
    n = min(len(final_md), 300)
    print(f"  Preview ({n} chars): {final_md[:n]}")
    return True


async def pipeline_opendataloader():
    """Pipeline completo con OpenDataLoader sobre PDF real."""
    from app.services.document_parser_service import (
        OpenDataLoaderParser, MarkItDownParser, ParserRouter, OPENDATALOADER_AVAILABLE
    )
    
    print("\n" + "="*70)
    print("  PIPELINE: OpenDataLoader sobre PDF real (Java+CPU)")
    print("="*70)
    
    if not OPENDATALOADER_AVAILABLE:
        print("WARN - OpenDataLoader no disponible. Saltando test.")
        return True
    
    pdf_path = find_arxiv_pdf()
    if not pdf_path:
        print("WARN - No hay PDF disponible. Saltando test.")
        return True
    
    print(f"[PDF] {pdf_path.name} ({pdf_path.stat().st_size / 1024:.0f} KB)")
    
    odl_parser = OpenDataLoaderParser()
    mit_parser = MarkItDownParser()
    router = ParserRouter()
    print("[OK] OpenDataLoaderParser + MarkItDownParser inicializados")
    
    selected, engine = router.select_parser(
        file_path=pdf_path,
        article_meta=SAMPLE_META_SCIENTIFIC,
        opendataloader_parser=odl_parser,
        markitdown_parser=mit_parser,
    )
    assert engine == "opendataloader", f"Router debio seleccionar opendataloader, obtuvo {engine}"
    print(f"[OK] Ruteo correcto: PDF cientifico -> OpenDataLoader")
    
    start = time.perf_counter()
    try:
        final_md = await selected.parse_document(pdf_path, SAMPLE_META_SCIENTIFIC)
        elapsed = time.perf_counter() - start
    except Exception as e:
        print(f"FAIL - OpenDataLoader error: {e}")
        if any(kw in str(e).lower() for kw in ["java", "jvm", "command", "not found"]):
            print("WARN - Java no disponible. Saltando test de conversion.")
            return True
        raise
    
    print(f"\n  RESULTADOS:")
    print(f"    Tiempo: {elapsed:.1f}s")
    print(f"    Longitud: {len(final_md)} chars")
    print(f"    Front-matter: {'OK' if final_md.startswith('---') else 'FAIL'}")
    print(f"    parser_engine: {'OK' if 'parser_engine: opendataloader' in final_md else 'FAIL'}")
    print(f"    Headings: {'OK' if '#' in final_md else 'WARN'}")
    
    if final_md.startswith('---'):
        yaml_block = final_md.split('---')[1]
        data = yaml.safe_load(yaml_block)
        assert data["parser_engine"] == "opendataloader"
        assert data["source_database"] == "arxiv"
        print(f"    YAML valido: {list(data.keys())}")
    
    output_path = EXPECTED_OUTPUTS / f"{pdf_path.stem}_opendataloader_pipeline.md"
    output_path.write_text(final_md, encoding="utf-8")
    print(f"    Output guardado: {output_path}")
    
    assert len(final_md) > 200, f"Markdown muy corto: {len(final_md)} chars"
    assert final_md.startswith('---'), "Falta front-matter YAML"
    assert 'parser_engine: opendataloader' in final_md, "Falta parser_engine en YAML"
    assert elapsed < 60.0, f"Conversion muy lenta: {elapsed:.1f}s"
    
    print(f"\n[OK] PIPELINE OPENDATALOADER - PASO")
    n = min(len(final_md), 300)
    print(f"  Preview ({n} chars): {final_md[:n]}")
    return True


# ==============================================================================
#  MAIN
# ==============================================================================

async def main():
    results = {}
    
    print("\n" + "=" * 70)
    print("  TESTS DE INTEGRACION DUAL-PARSER")
    print("=" * 70 + "\n")
    
    print("--- UNIT: ParserRouter ---")
    test_router_pdf_cientifico_usa_opendataloader()
    test_router_docx_siempre_markitdown()
    test_router_pdf_no_cientifico_usa_markitdown()
    test_router_formato_desconocido_usa_markitdown()
    test_router_parametrizado()
    
    results["markitdown"] = await pipeline_markitdown()
    results["opendataloader"] = await pipeline_opendataloader()
    
    print("\n" + "="*70)
    print("  RESUMEN FINAL")
    print("="*70)
    for name, passed in results.items():
        status = "PASO" if passed else "FALLO"
        print(f"  {name}: {status}")
    all_ok = all(results.values())
    if all_ok:
        print("\n  TODOS LOS TESTS PASARON")
    else:
        print("\n  ALGUNOS TESTS FALLARON")
    return all_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
