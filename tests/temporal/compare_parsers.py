"""
Archivo: compare_parsers.py
Modificación: 2026-05-17
Autor: Antigravity

Descripción:
Orquestador y comparador de rendimiento y calidad para los parsers de AgriSearch.
Ejecuta secuencialmente OpenDataLoader y MarkItDown sobre el mismo PDF científico,
evalúa la estructura extraída, detecta si el documento fue generado con LaTeX,
mide los tiempos de procesamiento y genera un informe de comparación detallado.

Acciones Principales:
    - Validación y clasificación del PDF (LaTeX vs. No-LaTeX).
    - Ejecución en paralelo/secuencia de ambos motores de parseo.
    - Extracción de métricas de calidad de texto y preservación de tablas.
    - Generación de un reporte comparativo impreso en consola.
    - Almacenamiento de las salidas de prueba en fixtures.

Estructura Interna:
    - `is_latex_pdf(pdf_path)`: Comprueba si el PDF proviene de LaTeX usando metadatos y fuentes.
    - `analyze_output(content)`: Analiza el Markdown generado buscando tablas, palabras y headings.
    - `main()`: Orquestador principal de la comparación.

Entradas / Dependencias:
    - Un archivo PDF en el directorio de descargas de AgriSearch.
    - Las dependencias de Python: `pypdf`, `pyyaml`, `opendataloader-pdf`, `markitdown`.

Salidas / Efectos:
    - Escribe `<pdf_name>_opendataloader.md` y `<pdf_name>_markitdown.md` en fixtures.
    - Produce un informe detallado impreso en consola.

Ejecución:
    uv run python tests/temporal/compare_parsers.py [--pdf PATH_TO_PDF]

Ejemplo de Uso:
    uv run python tests/temporal/compare_parsers.py --pdf backend/data/projects/Variables_derivadas_de_imagenes_espectrales/Busqueda_1/descargas/2020_Casal_Classifying_sleep-wake_stages_through_recurrent_ne.pdf
"""

import sys
import time
import argparse
import asyncio
import re
from pathlib import Path
from pypdf import PdfReader
import yaml

# Agregar directorio del backend al path de ejecución para resolver módulos internos
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.services.document_parser_service import (
    OpenDataLoaderParser,
    MarkItDownParser,
    OPENDATALOADER_AVAILABLE,
    MARKITDOWN_AVAILABLE
)


def is_latex_pdf(pdf_path: Path) -> dict:
    """
    Detecta si un PDF fue generado por LaTeX analizando sus metadatos y fuentes.

    Args:
        pdf_path (Path): Ruta al archivo PDF.

    Returns:
        dict: Detalles de la detección de LaTeX.
    """
    result = {
        "is_latex": False,
        "reason": "No se encontraron firmas de LaTeX.",
        "creator": "Desconocido",
        "producer": "Desconocido",
        "ptex_banner": "N/A",
        "latex_fonts": []
    }
    
    try:
        reader = PdfReader(pdf_path)
        meta = reader.metadata
        
        # 1. Metadatos estándar
        if meta:
            creator = str(meta.get("/Creator", "")).lower()
            producer = str(meta.get("/Producer", "")).lower()
            ptex = str(meta.get("/PTEX.Fullbanner", "")).lower()
            
            result["creator"] = meta.get("/Creator", "Desconocido")
            result["producer"] = meta.get("/Producer", "Desconocido")
            if "/PTEX.Fullbanner" in meta:
                result["ptex_banner"] = meta["/PTEX.Fullbanner"]
                
            # Buscar palabras clave altamente específicas asociadas a LaTeX/TeX
            # Excluimos "tex" genérico para evitar falsos positivos con "PDFContext", "text", etc.
            latex_keywords = ["latex", "pdftex", "luatex", "xetex", "dvips", "distiller", "dvipdf", "miktex", "mactex"]
            for kw in latex_keywords:
                if kw in creator or kw in producer or kw in ptex:
                    result["is_latex"] = True
                    result["reason"] = f"Firma '{kw}' encontrada en los metadatos."
                    return result

            # Buscar "tex" con límites de palabra para evitar "PDFContext"
            if re.search(r"\btex\b", creator) or re.search(r"\btex\b", producer) or "tex" in ptex:
                result["is_latex"] = True
                result["reason"] = "Firma 'tex' independiente encontrada en los metadatos."
                return result

        # 2. Análisis de Fuentes de la biblioteca de fuentes TeX
        latex_font_signatures = ["CM", "LM", "NimbusRom", "SFTT", "CMMI", "CMR", "CMSY", "CMEX", "URWBookman"]
        found_latex_fonts = set()
        
        for page in reader.pages[:3]:
            if "/Resources" in page and "/Font" in page["/Resources"]:
                font_dict = page["/Resources"]["/Font"]
                for font_key in font_dict:
                    font_obj = font_dict[font_key]
                    if "/BaseFont" in font_obj:
                        base_font = str(font_obj["/BaseFont"])
                        clean_font = base_font.split("+")[-1] if "+" in base_font else base_font
                        for sig in latex_font_signatures:
                            if clean_font.startswith(sig) or sig in clean_font:
                                found_latex_fonts.add(clean_font)
                                
        if found_latex_fonts:
            result["latex_fonts"] = list(found_latex_fonts)
            result["is_latex"] = True
            result["reason"] = f"Fuentes de LaTeX detectadas en el documento: {list(found_latex_fonts)}"
            
    except Exception as e:
        result["reason"] = f"Error leyendo el PDF: {str(e)}"
        
    return result


def analyze_output(content: str) -> dict:
    """
    Analiza el Markdown generado para extraer métricas de calidad.

    Args:
        content (str): Contenido Markdown completo.

    Returns:
        dict: Métricas analizadas.
    """
    # 1. Contar palabras y caracteres
    words = len(content.split())
    chars = len(content)
    
    # 2. Contar títulos/headings
    headings = len(re.findall(r"^#{1,6}\s+", content, re.MULTILINE))
    
    # 3. Contar tablas aplanadas (patrón 'se registra:' inyectado por TableFlattener)
    flattened_table_rows = len(re.findall(r"se registra:", content))
    
    # 4. Contar tablas markdown clásicas residuales
    raw_table_lines = len([line for line in content.split("\n") if "|" in line])
    
    return {
        "words": words,
        "chars": chars,
        "headings": headings,
        "flattened_rows": flattened_table_rows,
        "raw_table_lines": raw_table_lines,
    }


async def main():
    """
    Punto de entrada principal para el comparador.
    """
    parser = argparse.ArgumentParser(description="Comparador de Parsers de AgriSearch.")
    parser.add_argument("--pdf", type=str, help="Ruta al PDF a comparar.")
    args = parser.parse_args()
    
    # 1. Verificar motores
    print("\n" + "="*80)
    print("      DIAGNÓSTICO Y COMPARACIÓN DE MOTORES DUAL-PARSER")
    print("="*80)
    print(f"  OpenDataLoader disponible: {'SÍ' if OPENDATALOADER_AVAILABLE else 'NO (Requiere Java + opendataloader-pdf)'}")
    print(f"  Microsoft MarkItDown disponible: {'SÍ' if MARKITDOWN_AVAILABLE else 'NO (Requiere markitdown)'}")
    
    if not OPENDATALOADER_AVAILABLE or not MARKITDOWN_AVAILABLE:
        print("[WARN] Uno o ambos motores no están completamente instalados. La comparación podría fallar.")
        
    # 2. Seleccionar PDF
    pdf_path = None
    if args.pdf:
        pdf_path = Path(args.pdf)
    else:
        sample_inputs_dir = ROOT_DIR / "tests" / "backend" / "integration" / "fixtures" / "sample_inputs"
        if sample_inputs_dir.exists():
            # Casal es excelente para tests rápidos y limpios
            casal_pdf = sample_inputs_dir / "2020_Casal_Classifying_sleep-wake_stages_through_recurrent_ne.pdf"
            if casal_pdf.exists():
                pdf_path = casal_pdf
            else:
                pdfs = list(sample_inputs_dir.glob("*.pdf"))
                if pdfs:
                    pdf_path = pdfs[0]
                    
    if not pdf_path or not pdf_path.exists():
        print(f"[ERROR] No se pudo localizar el PDF de prueba. Ruta: {args.pdf}")
        sys.exit(1)
        
    print(f"\n[CONFIG] PDF Seleccionado:")
    print(f"  Nombre: {pdf_path.name}")
    print(f"  Tamaño: {pdf_path.stat().st_size / (1024*1024):.2f} MB")
    
    # 3. Detectar LaTeX
    print("\n" + "-"*40 + " PASO 1: DETECCIÓN LA-TEX " + "-"*40)
    latex_info = is_latex_pdf(pdf_path)
    print(f"  ¿Es un PDF de LaTeX?: {'SÍ' if latex_info['is_latex'] else 'NO'}")
    print(f"  Razón principal: {latex_info['reason']}")
    print(f"  Creador: {latex_info['creator']}")
    print(f"  Productor: {latex_info['producer']}")
    print(f"  pdfTeX Banner: {latex_info['ptex_banner']}")
    if latex_info["latex_fonts"]:
        print(f"  Fuentes LaTeX encontradas: {latex_info['latex_fonts']}")
        
    # Explicación del comportamiento según la detección
    print("\n  [ANÁLISIS TEÓRICO]:")
    if latex_info["is_latex"]:
        print("    --> Este documento fue creado con LaTeX. Los PDFs de LaTeX tienen flujos de texto y")
        print("        tipografía extremadamente limpios. OpenDataLoader los procesa con gran robustez")
        print("        en dos columnas y mantiene la estructura lógica perfecta del artículo científico.")
    else:
        print("    --> Este documento no es de LaTeX (probablemente Word, PowerPoint o escaneado).")
        print("        Su layout puede ser más irregular. MarkItDown o motores con OCR son excelentes fallbacks.")
        
    # 4. Configurar metadatos simulados
    mock_meta = {
        "id": f"comp-{pdf_path.stem[:15]}",
        "doi": "10.48550/comparison",
        "title": pdf_path.stem.replace("_", " "),
        "authors": "Integrator / Test Runner",
        "year": 2026,
        "journal": "AgriSearch Comparative Benchmarking",
        "keywords": ["spectral images", "comparison", "latex"],
        "source_database": "arxiv",
        "is_latex_source": latex_info["is_latex"]
    }
    
    fixtures_dir = ROOT_DIR / "tests" / "backend" / "integration" / "fixtures" / "expected_outputs"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    
    # 5. Ejecutar OpenDataLoader
    print("\n" + "-"*40 + " PASO 2: PARSEO CON OPENDATALOADER " + "-"*40)
    odl_content = ""
    odl_time = 0.0
    if OPENDATALOADER_AVAILABLE:
        try:
            parser_odl = OpenDataLoaderParser()
            start = time.perf_counter()
            odl_content = await parser_odl.parse_pdf(pdf_path, mock_meta)
            odl_time = time.perf_counter() - start
            
            output_odl = fixtures_dir / f"{pdf_path.stem}_opendataloader.md"
            output_odl.write_text(odl_content, encoding="utf-8")
            print(f"  [OK] Procesado con OpenDataLoader en {odl_time:.2f} segundos.")
            print(f"  [OK] Guardado en: {output_odl.name}")
        except Exception as e:
            print(f"  [FAIL] Error en OpenDataLoader: {e}")
    else:
        print("  [SALTADO] OpenDataLoader no está instalado.")
        
    # 6. Ejecutar MarkItDown
    print("\n" + "-"*40 + " PASO 3: PARSEO CON MICROSOFT MARKITDOWN " + "-"*40)
    mit_content = ""
    mit_time = 0.0
    if MARKITDOWN_AVAILABLE:
        try:
            parser_mit = MarkItDownParser()
            start = time.perf_counter()
            mit_content = await parser_mit.parse_pdf(pdf_path, mock_meta)
            mit_time = time.perf_counter() - start
            
            output_mit = fixtures_dir / f"{pdf_path.stem}_markitdown.md"
            output_mit.write_text(mit_content, encoding="utf-8")
            print(f"  [OK] Procesado con MarkItDown en {mit_time:.2f} segundos.")
            print(f"  [OK] Guardado en: {output_mit.name}")
        except Exception as e:
            print(f"  [FAIL] Error en MarkItDown: {e}")
    else:
        print("  [SALTADO] MarkItDown no está instalado.")
        
    # 7. Comparar y Reportar
    print("\n" + "="*80)
    print("                         CUADRO COMPARATIVO FINAL")
    print("="*80)
    
    odl_metrics = analyze_output(odl_content) if odl_content else None
    mit_metrics = analyze_output(mit_content) if mit_content else None
    
    print(f"  MÉTRICA                         | OPENDATALOADER        | MARKITDOWN")
    print(f"  " + "-"*32 + "+" + "-"*23 + "+" + "-"*23)
    
    # Tiempo
    print(f"  Tiempo de Procesamiento         | {f'{odl_time:.2f} s':<21} | {f'{mit_time:.2f} s':<21}")
    
    # Longitud texto
    char_str_odl = f"{odl_metrics['chars']:,} caract." if odl_metrics else "N/A"
    char_str_mit = f"{mit_metrics['chars']:,} caract." if mit_metrics else "N/A"
    print(f"  Caracteres Totales              | {char_str_odl:<21} | {char_str_mit:<21}")
    
    word_str_odl = f"{odl_metrics['words']:,} pal." if odl_metrics else "N/A"
    word_str_mit = f"{mit_metrics['words']:,} pal." if mit_metrics else "N/A"
    print(f"  Palabras Totales                | {word_str_odl:<21} | {word_str_mit:<21}")
    
    # Estructura
    head_str_odl = f"{odl_metrics['headings']} títulos" if odl_metrics else "N/A"
    head_str_mit = f"{mit_metrics['headings']} títulos" if mit_metrics else "N/A"
    print(f"  Títulos (Headings)              | {head_str_odl:<21} | {head_str_mit:<21}")
    
    # Tablas
    tab_str_odl = f"{odl_metrics['flattened_rows']} filas aplanadas" if odl_metrics else "N/A"
    tab_str_mit = f"{mit_metrics['flattened_rows']} filas aplanadas" if mit_metrics else "N/A"
    print(f"  Tablas Aplanadas (RAG)          | {tab_str_odl:<21} | {tab_str_mit:<21}")
    
    raw_tab_odl = f"{odl_metrics['raw_table_lines']} líneas residuales" if odl_metrics else "N/A"
    raw_tab_mit = f"{mit_metrics['raw_table_lines']} líneas residuales" if mit_metrics else "N/A"
    print(f"  Tablas Crudas Residuales        | {raw_tab_odl:<21} | {raw_tab_mit:<21}")
    
    print(f"  " + "-"*32 + "+" + "-"*23 + "+" + "-"*23)
    
    # 8. Recomendación de uso basada en heurística
    print("\n[RECOMENDACIÓN FINAL DE EXTRACCIÓN]:")
    if latex_info["is_latex"]:
        print("  >> Se confirma que el PDF proviene de LaTeX.")
        print("  >> RECOMENDACIÓN: Utilizar estrictamente OPENDATALOADER.")
        print("     Ofrece una reconstrucción de layout científica de altísimo nivel y preservación")
        print("     estructural de tablas, minimizando la pérdida de contexto matemático/técnico.")
    else:
        print("  >> El PDF no proviene de LaTeX.")
        print("  >> RECOMENDACIÓN: Utilizar MARKITDOWN con soporte de VLM (Ollama/gemma4) o un OCR potente.")
        print("     Los documentos no-LaTeX frecuentemente contienen tablas integradas como imágenes o")
        print("     layouts desordenados donde un parser secuencial inteligente asistido por OCR o")
        print("     análisis visual produce resultados superiores.")
        
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
