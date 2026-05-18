"""
Archivo: import_benchmarking_pdfs.py
Modificación: 2026-05-17
Autor: Antigravity

Descripción:
Script utilitario para importar un set de referencia de al menos 20 artículos
científicos netos desde el directorio de descargas del proyecto hacia las
fixtures de integración `tests/backend/integration/fixtures/sample_inputs/`.
Clasifica los PDFs usando la heurística de detección de LaTeX para priorizar
los documentos con la estructura tipográfica más rica.

Acciones Principales:
    - Escaneo recursivo de PDFs en el directorio de descargas.
    - Clasificación en tiempo real de cada PDF (LaTeX vs. No-LaTeX).
    - Selección inteligente y copia de exactamente 20 artículos científicos.
    - Creación de un reporte resumen del set de benchmarking importado.

Estructura Interna:
    - `is_latex_pdf(pdf_path)`: Clasifica el PDF y detecta la firma de compilación.
    - `main()`: Orquestador de la copia y catalogación de los PDFs de referencia.

Entradas / Dependencias:
    - Directorio de descargas original con artículos científicos.
    - Librerías: `pypdf`, `shutil`, `pathlib`.

Salidas / Efectos:
    - Copia exactamente 20 archivos PDF a `tests/backend/integration/fixtures/sample_inputs/`.
    - Imprime una tabla resumen con la clasificación del set de benchmarking.

Ejecución:
    uv run python tests/temporal/import_benchmarking_pdfs.py
"""

import sys
import shutil
import re
from pathlib import Path
from pypdf import PdfReader

# Configurar path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DOWNLOADS_DIR = ROOT_DIR / "backend" / "data" / "projects" / "Variables_derivadas_de_imagenes_espectrales" / "Busqueda_1" / "descargas"
SAMPLE_INPUTS_DIR = ROOT_DIR / "tests" / "backend" / "integration" / "fixtures" / "sample_inputs"


def is_latex_pdf(pdf_path: Path) -> dict:
    """
    Detecta si un PDF fue generado por LaTeX analizando sus metadatos y fuentes.
    """
    result = {
        "is_latex": False,
        "creator": "Desconocido",
        "producer": "Desconocido"
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
            
            # Palabras clave específicas
            latex_keywords = ["latex", "pdftex", "luatex", "xetex", "dvips", "distiller", "dvipdf", "miktex", "mactex"]
            for kw in latex_keywords:
                if kw in creator or kw in producer or kw in ptex:
                    result["is_latex"] = True
                    return result
            
            # Exclusión de falsos positivos en Quartz PDFContext usando límite de palabra
            if re.search(r"\btex\b", creator) or re.search(r"\btex\b", producer) or "tex" in ptex:
                result["is_latex"] = True
                return result

        # 2. Análisis de Fuentes
        latex_font_signatures = ["CM", "LM", "NimbusRom", "SFTT", "CMMI", "CMR", "CMSY", "CMEX", "URWBookman"]
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
                                result["is_latex"] = True
                                return result
                                
    except Exception:
        pass
        
    return result


def main():
    """
    Punto de entrada para el importador de PDFs de benchmarking.
    """
    print("\n" + "="*80)
    print("      IMPORTADOR Y CATALOGADOR DE ARTÍCULOS DE BENCHMARKING (SET DE 20)")
    print("="*80)
    
    if not DOWNLOADS_DIR.exists():
        print(f"[ERROR] El directorio de descargas no existe: {DOWNLOADS_DIR}")
        sys.exit(1)
        
    SAMPLE_INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Escanear todos los PDFs disponibles
    all_pdfs = list(DOWNLOADS_DIR.glob("*.pdf"))
    print(f"  Total de PDFs encontrados en descargas: {len(all_pdfs)}")
    
    # 2. Clasificar los PDFs en LaTeX y No-LaTeX
    latex_pdfs = []
    other_pdfs = []
    
    print("\n  [PROCESO] Clasificando PDFs de origen en tiempo real...")
    for idx, pdf in enumerate(all_pdfs):
        info = is_latex_pdf(pdf)
        if info["is_latex"]:
            latex_pdfs.append((pdf, info))
        else:
            other_pdfs.append((pdf, info))
            
    print(f"  -> Encontrados {len(latex_pdfs)} artículos LaTeX auténticos.")
    print(f"  -> Encontrados {len(other_pdfs)} otros documentos/PDFs.")
    
    # 3. Seleccionar los 20 mejores artículos científicos netos
    # Damos máxima prioridad a los artículos de LaTeX, y si faltan para completar 20, usamos otros científicos
    selected = []
    
    # Prioridad 1: PDFs de LaTeX
    for pdf, info in latex_pdfs[:20]:
        selected.append((pdf, info, "LaTeX"))
        
    # Prioridad 2: Fallback con otros PDFs si faltan
    if len(selected) < 20:
        needed = 20 - len(selected)
        for pdf, info in other_pdfs[:needed]:
            selected.append((pdf, info, "Standard/Word"))
            
    print(f"\n  [PROCESO] Copiando exactamente {len(selected)} artículos de referencia seleccionados...")
    
    # 4. Copiar los archivos seleccionados
    copied_count = 0
    print("\n" + "-"*80)
    print("  N°  | NOMBRE DEL DOCUMENTO                               | TIPO      | CREADOR")
    print("-"*80)
    
    for idx, (pdf, info, category) in enumerate(selected, 1):
        dest_path = SAMPLE_INPUTS_DIR / pdf.name
        try:
            shutil.copy2(pdf, dest_path)
            copied_count += 1
            creator_short = info["creator"][:22]
            print(f"  {idx:<3} | {pdf.name[:48]:<50} | {category:<9} | {creator_short:<22}")
        except Exception as e:
            print(f"  {idx:<3} | [FAIL] {pdf.name[:40]:<42} | {category:<9} | Error: {e}")
            
    print("-"*80)
    print(f"\n[OK] Importación finalizada con éxito.")
    print(f"  Total de archivos PDF de benchmarking en sample_inputs: {copied_count}")
    print(f"  Directorio destino: {SAMPLE_INPUTS_DIR.resolve()}\n")


if __name__ == "__main__":
    main()
