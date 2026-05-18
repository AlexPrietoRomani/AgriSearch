"""
Archivo: run_markitdown.py
Modificación: 2026-05-17
Autor: Antigravity

Descripción:
Script de ejecución estricta para el motor de parseo Microsoft MarkItDown.
Realiza la conversión de un artículo científico en PDF a Markdown enriquecido.
Analiza si el PDF fue generado con LaTeX mediante metadatos y análisis de fuentes,
y deposita el archivo de salida en las fixtures de integración.

Acciones Principales:
    - Detección heurística de la generación de PDF con LaTeX.
    - Carga e inicialización del motor MarkItDownParser en modo CPU puro.
    - Conversión del PDF a Markdown aplanando las tablas complejas para RAG.
    - Almacenamiento del Markdown enriquecido en la carpeta de fixtures.
    - Reporte detallado de tiempos y manejo de elementos tabulares.

Estructura Interna:
    - `is_latex_pdf(pdf_path)`: Comprueba si el PDF proviene de LaTeX usando metadatos y fuentes.
    - `main()`: Orquestador principal de la ejecución del script.

Entradas / Dependencias:
    - Un archivo PDF en el directorio de descargas de AgriSearch.
    - La dependencia de Python: `markitdown`, `pypdf`, `pyyaml`.

Salidas / Efectos:
    - Genera un archivo Markdown enriquecido en `tests/backend/integration/fixtures/expected_outputs/`.

Ejecución:
    uv run python tests/temporal/run_markitdown.py [--pdf PATH_TO_PDF]

Ejemplo de Uso:
    uv run python tests/temporal/run_markitdown.py --pdf backend/data/projects/Variables_derivadas_de_imagenes_espectrales/Busqueda_1/descargas/2020_Casal_Classifying_sleep-wake_stages_through_recurrent_ne.pdf

Argumentos:
    - --pdf: str - Ruta opcional a un archivo PDF específico para parsear.
"""

import sys
import time
import argparse
import asyncio
from pathlib import Path
from pypdf import PdfReader
import yaml

# Agregar directorio del backend al path de ejecución para resolver módulos internos
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.services.document_parser_service import MarkItDownParser, MARKITDOWN_AVAILABLE


def is_latex_pdf(pdf_path: Path) -> dict:
    """
    Detecta si un PDF fue generado por LaTeX analizando sus metadatos y fuentes.

    Args:
        pdf_path (Path): Ruta al archivo PDF.

    Returns:
        dict: Un diccionario con los detalles de la detección:
              - 'is_latex' (bool): True si se detecta LaTeX.
              - 'reason' (str): Justificación de la decisión.
              - 'creator' (str): Valor del metadato Creator.
              - 'producer' (str): Valor del metadato Producer.
              - 'ptex_banner' (str): Banner de pdfTeX si existe.
              - 'latex_fonts' (list): Lista de fuentes LaTeX detectadas.
    """
    result = {
        "is_latex": False,
        "reason": "No se encontraron indicadores de LaTeX.",
        "creator": "Desconocido",
        "producer": "Desconocido",
        "ptex_banner": "N/A",
        "latex_fonts": []
    }
    
    try:
        reader = PdfReader(pdf_path)
        meta = reader.metadata
        
        # 1. Analizar metadatos estándar
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
                    result["reason"] = f"Detectado indicador '{kw}' en los metadatos del PDF."
                    return result

            # Buscar "tex" con límites de palabra para evitar "PDFContext"
            import re
            if re.search(r"\btex\b", creator) or re.search(r"\btex\b", producer) or "tex" in ptex:
                result["is_latex"] = True
                result["reason"] = "Detectado indicador 'tex' independiente en los metadatos."
                return result

        # 2. Analizar fuentes (si los metadatos fallan o están vacíos)
        # Escaneamos las primeras 3 páginas en busca de fuentes estándar de TeX (Computer Modern / Latin Modern)
        latex_font_signatures = ["CM", "LM", "NimbusRom", "SFTT", "CMMI", "CMR", "CMSY", "CMEX", "URWBookman"]
        found_latex_fonts = set()
        
        for page in reader.pages[:3]:
            if "/Resources" in page and "/Font" in page["/Resources"]:
                font_dict = page["/Resources"]["/Font"]
                for font_key in font_dict:
                    font_obj = font_dict[font_key]
                    if "/BaseFont" in font_obj:
                        base_font = str(font_obj["/BaseFont"])
                        # Quitar prefijo de subset de fuentes (ej. ABCDEF+FontName -> FontName)
                        clean_font = base_font.split("+")[-1] if "+" in base_font else base_font
                        
                        for sig in latex_font_signatures:
                            if clean_font.startswith(sig) or sig in clean_font:
                                found_latex_fonts.add(clean_font)
                                
        if found_latex_fonts:
            result["latex_fonts"] = list(found_latex_fonts)
            result["is_latex"] = True
            result["reason"] = f"Se detectaron fuentes típicas de LaTeX: {list(found_latex_fonts)}"
            
    except Exception as e:
        result["reason"] = f"Error al leer la estructura interna del PDF: {str(e)}"
        
    return result


async def main():
    """
    Punto de entrada principal para el script de MarkItDown.
    """
    parser = argparse.ArgumentParser(description="Parser estricto MarkItDown.")
    parser.add_argument("--pdf", type=str, help="Ruta al PDF a procesar.")
    args = parser.parse_args()
    
    # 1. Validar disponibilidad de MarkItDown
    if not MARKITDOWN_AVAILABLE:
        print("[ERROR] Microsoft MarkItDown no está instalado.")
        print("Por favor, asegúrate de instalar el paquete: uv add 'markitdown[pdf]'.")
        sys.exit(1)
        
    # 2. Localizar el PDF
    pdf_path = None
    if args.pdf:
        pdf_path = Path(args.pdf)
    else:
        # Default: Buscar un PDF científico en la carpeta de fixtures de sample_inputs
        sample_inputs_dir = ROOT_DIR / "tests" / "backend" / "integration" / "fixtures" / "sample_inputs"
        if sample_inputs_dir.exists():
            casal_pdf = sample_inputs_dir / "2020_Casal_Classifying_sleep-wake_stages_through_recurrent_ne.pdf"
            if casal_pdf.exists():
                pdf_path = casal_pdf
            else:
                # Usar el primer PDF disponible
                pdfs = list(sample_inputs_dir.glob("*.pdf"))
                if pdfs:
                    pdf_path = pdfs[0]
                    
    if not pdf_path or not pdf_path.exists():
        print(f"[ERROR] No se pudo encontrar un PDF válido. Ruta especificada: {args.pdf}")
        sys.exit(1)
        
    print(f"\n[INICIO] Iniciando procesamiento estricto con MarkItDown")
    print(f"  Archivo: {pdf_path}")
    print(f"  Tamaño: {pdf_path.stat().st_size / 1024:.2f} KB")
    
    # 3. Detectar LaTeX
    print("\n[PASO 1] Ejecutando análisis de generación LaTeX...")
    latex_info = is_latex_pdf(pdf_path)
    print(f"  ¿Es un PDF de LaTeX?: {'SÍ' if latex_info['is_latex'] else 'NO'}")
    print(f"  Razón: {latex_info['reason']}")
    print(f"  Creator: {latex_info['creator']}")
    print(f"  Producer: {latex_info['producer']}")
    print(f"  pdfTeX Banner: {latex_info['ptex_banner']}")
    if latex_info["latex_fonts"]:
        print(f"  Fuentes LaTeX encontradas: {latex_info['latex_fonts']}")
        
    # 4. Configurar metadatos simulados para inyectar en el Front-matter
    mock_meta = {
        "id": f"mit-test-{pdf_path.stem[:15]}",
        "doi": "10.48550/mock.doi",
        "title": pdf_path.stem.replace("_", " "),
        "authors": "Casal et al. / Test Runner",
        "year": 2020,
        "journal": "AgriSearch Integration Test",
        "keywords": ["spectral images", "latex comparison", "markitdown"],
        "source_database": "arxiv",
    }
    
    # Agregar información de LaTeX a los metadatos
    mock_meta["is_latex_source"] = latex_info["is_latex"]
    mock_meta["pdf_creator"] = latex_info["creator"]
    
    # 5. Inicializar parser y ejecutar conversión
    print("\n[PASO 2] Convirtiendo PDF a Markdown con MarkItDownParser (CPU)...")
    mit = MarkItDownParser()
    
    start_time = time.perf_counter()
    try:
        markdown_output = await mit.parse_pdf(
            pdf_path=pdf_path,
            article_meta=mock_meta
        )
        elapsed = time.perf_counter() - start_time
        print(f"  [OK] Conversión completada con éxito en {elapsed:.2f} segundos.")
        print(f"  Longitud del Markdown generado: {len(markdown_output)} caracteres.")
        
    except Exception as e:
        print(f"  [ERROR] Falló la conversión: {e}")
        sys.exit(1)
        
    # 6. Almacenar el archivo en las fixtures de integración
    fixtures_outputs_dir = ROOT_DIR / "tests" / "backend" / "integration" / "fixtures" / "expected_outputs"
    fixtures_outputs_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = fixtures_outputs_dir / f"{pdf_path.stem}_markitdown.md"
    output_file.write_text(markdown_output, encoding="utf-8")
    print(f"\n[PASO 3] Archivo guardado en fixtures:")
    print(f"  Destino: {output_file.resolve()}")
    
    # 7. Imprimir un pequeño análisis del manejo de tablas
    print("\n[PASO 4] Análisis de Tablas en el Markdown resultante:")
    # Buscar si se inyectaron aplanados de tablas
    flattened_tables = [line for line in markdown_output.split("\n") if "se registra:" in line]
    if flattened_tables:
        print(f"  Se detectaron y aplanaron {len(flattened_tables)} filas de tabla con éxito.")
        print("  Ejemplo de fila de tabla aplanada:")
        print(f"    > {flattened_tables[0][:150]}...")
    else:
        print("  No se detectaron tablas tradicionales en el Markdown resultante o no fue necesario aplanarlas.")
        # Buscar tablas markdown tradicionales por si acaso
        raw_tables = [line for line in markdown_output.split("\n") if "|" in line]
        if raw_tables:
            print(f"  Nota: Se encontraron {len(raw_tables)} líneas que contienen '|', es posible que existan tablas sin aplanar.")
            
    print("\n[FIN] Ejecución de MarkItDown finalizada correctamente.\n")


if __name__ == "__main__":
    asyncio.run(main())
