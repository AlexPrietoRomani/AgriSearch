"""
Archivo: inspect_pdf_metadata.py
Modificación: 2026-05-17
Autor: Antigravity

Descripción:
Script utilitario para inspeccionar los metadatos y fuentes de los PDFs en el directorio de descargas.
Ayuda a determinar patrones comunes de generación con LaTeX u otras herramientas.

Ejecución:
    python tests/temporal/inspect_pdf_metadata.py
"""

import os
from pathlib import Path
from pypdf import PdfReader

DOWNLOADS_DIR = Path(r"c:\Users\ALEX\Github\AgriSearch\backend\data\projects\Variables_derivadas_de_imagenes_espectrales\Busqueda_1\descargas")

def analyze_pdf(pdf_path: Path):
    """
    Analiza un archivo PDF e imprime su metadata y fuentes para detectar LaTeX.
    """
    print(f"\n--- Analizando: {pdf_path.name} ---")
    try:
        reader = PdfReader(pdf_path)
        meta = reader.metadata
        
        print("Metadatos:")
        if meta:
            for key, val in meta.items():
                print(f"  {key}: {val}")
        else:
            print("  Sin metadatos encontrados.")
            
        # Intentar extraer fuentes de las primeras 3 páginas para evitar lentitud
        fonts = set()
        for idx, page in enumerate(reader.pages[:3]):
            if "/Resources" in page and "/Font" in page["/Resources"]:
                font_dict = page["/Resources"]["/Font"]
                for font_key in font_dict:
                    font_obj = font_dict[font_key]
                    if "/BaseFont" in font_obj:
                        fonts.add(str(font_obj["/BaseFont"]))
                        
        print("Fuentes detectadas (primeras 3 páginas):")
        for font in sorted(fonts):
            print(f"  {font}")
            
    except Exception as e:
        print(f"Error analizando {pdf_path.name}: {e}")

def main():
    if not DOWNLOADS_DIR.exists():
        print(f"El directorio no existe: {DOWNLOADS_DIR}")
        return
        
    pdf_files = list(DOWNLOADS_DIR.glob("*.pdf"))
    print(f"Encontrados {len(pdf_files)} archivos PDF.")
    
    # Analizar los primeros 5 PDFs para ver sus firmas
    for pdf_path in pdf_files[:5]:
        analyze_pdf(pdf_path)

if __name__ == "__main__":
    main()
