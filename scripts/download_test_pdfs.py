"""
Archivo: download_test_pdfs.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Script de automatización para la descarga de artículos científicos (PDF) desde arXiv.
Estos archivos se utilizan como assets para pruebas de parsing y Active Learning.

Acciones Principales:
    - Descarga asíncrona de múltiples PDFs simultáneamente.
    - Validación de existencia previa para evitar descargas redundantes.
    - Gestión de errores HTTP y reportes de progreso en consola.

Estructura Interna:
    - `download_pdf`: Gestor de descarga individual por paper ID.
    - `main`: Orquestador asíncrono de tareas de red.

Entradas / Dependencias:
    - Conexión a internet.
    - Librería `aiohttp` para peticiones asíncronas.

Salidas / Efectos:
    - Descarga archivos .pdf en `tests/assets/pdf/`.

Ejecución:
    uv run python scripts/download_test_pdfs.py
"""
import asyncio
import aiohttp
from pathlib import Path

PDFS = [
    ("2504.10522v1", "ndvi_crop_health.pdf"),
    ("2502.08678v1", "multispectral_weed_detection.pdf"),
    ("2012.11486v1", "leaf_segmentation.pdf"),
    ("2108.10054v1", "remote_sensing_crop_production.pdf"),
    ("2306.06288v1", "sage_ndvi.pdf"),
    ("2510.23382v1", "crop_type_mapping.pdf"),
]

OUTPUT_DIR = Path(__file__).parent.parent / "tests" / "assets" / "pdf"

async def download_pdf(session: aiohttp.ClientSession, paper_id: str, filename: str):
    """
    Descarga un archivo PDF desde el repositorio de arXiv de forma asíncrona.

    Args:
        session (aiohttp.ClientSession): Sesión HTTP compartida para las peticiones.
        paper_id (str): Identificador único del paper en arXiv (ej: '2301.12345v1').
        filename (str): Nombre deseado para el archivo descargado localmente.

    Returns:
        bool: True si la descarga fue exitosa o el archivo ya existía, False si hubo error.

    Salidas / Efectos:
        - Escribe el contenido binario del PDF en el disco.
        - Muestra mensajes de estado en la consola.
    """
    url = f"https://arxiv.org/pdf/{paper_id}"
    output_path = OUTPUT_DIR / filename
    if output_path.exists():
        print(f"  [OK] {filename} ya existe")
        return True
    
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                content = await resp.read()
                output_path.write_bytes(content)
                size_mb = len(content) / (1024 * 1024)
                print(f"  [OK] {filename} ({paper_id}) — {size_mb:.1f} MB")
                return True
            else:
                print(f"  [ERROR] {filename} — HTTP {resp.status}")
                return False
    except Exception as e:
        print(f"  [ERROR] {filename} — {e}")
        return False

async def main():
    """
    Orquestador principal para la descarga masiva de artículos de prueba.
    Gestiona la creación del directorio de salida y la ejecución paralela de descargas.

    Salidas / Efectos:
        - Crea el directorio `tests/assets/pdf` si no existe.
        - Descarga los archivos definidos en la constante `PDFS`.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Descargando {len(PDFS)} PDFs en {OUTPUT_DIR}...")
    
    async with aiohttp.ClientSession() as session:
        tasks = [download_pdf(session, pid, fname) for pid, fname in PDFS]
        results = await asyncio.gather(*tasks)
    
    ok = sum(results)
    print(f"\n{ok}/{len(PDFS)} PDFs descargados correctamente")

if __name__ == "__main__":
    asyncio.run(main())
