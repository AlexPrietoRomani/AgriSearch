import asyncio
import pytest
import os
import requests
from pathlib import Path
import sys

# Añadir el path de backend para encontrar 'app'
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.document_parser_service import MarkItDownParser
import logging

# Configurar logging para ver la salida del Parser en consola
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

@pytest.mark.skip(reason="Este es un test manual que descarga un PDF real de ArXiv. Ejecutar solo cuando sea necesario.")
async def test_real_arxiv_conversion():
    """
    TASK 2.0.8: Test de integración real.
    Descarga un paper de ArXiv y lo convierte a Markdown usando MarkItDown.
    """
    arxiv_url = "https://arxiv.org/pdf/2507.09375v1"
    paper_id = "2507.09375v1"
    
    # Directorios de trabajo
    output_dir = Path(__file__).parent / "outputs"
    output_dir.mkdir(exist_ok=True)
    
    temp_pdf = output_dir / f"{paper_id}.pdf"
    output_md = output_dir / f"arxiv_{paper_id}.md"
    
    print(f"\n[INFO] Descargando PDF de ArXiv: {arxiv_url}...")
    # Descarga síncrona con requests está bien para este script de test
    response = requests.get(arxiv_url)
    response.raise_for_status()
    temp_pdf.write_bytes(response.content)
    print(f"[OK] PDF guardado en: {temp_pdf}")
    
    # Inicializar parser con VLM habilitado (Usando el puente de Ollama)
    print("[WAIT] Inicializando MarkItDownParser con VLM (Ollama) y convirtiendo...")
    # Pasamos la URL de Ollama como llm_client; el Parser instanciará el OllamaVLMWrapper automáticamente
    parser = MarkItDownParser(
        llm_client="http://localhost:11434/v1", 
        llm_model="gemma4:26b"
    )
    
    # Simular metadata para el front-matter
    dummy_meta = {
        "id": paper_id,
        "title": "Automated Multi-Class Crop Pathology Classification",
        "doi": "10.48550/arXiv.2507.09375",
        "authors": "Sourish Suri, Yifei Shao",
        "year": 2025,
        "journal": "ArXiv",
        "source_database": "arxiv"
    }
    
    # Conversión (AWAIT!)
    result = await parser.parse_pdf(str(temp_pdf), article_meta=dummy_meta)
    
    # Guardar resultado
    output_md.write_text(result, encoding="utf-8")
    print(f"[SUCCESS] Conversion completada! Archivo generado: {output_md}")
    
    # Verificaciones básicas
    assert len(result) > 1000
    assert "YAML" not in result # MarkItDownParser.parse_pdf devuelve el contenido crudo, el enriquecimiento añade el YAML
    assert "# Abstract" in result or "ABSTRACT" in result or "Abstract" in result

if __name__ == "__main__":
    # Si se ejecuta directamente, llamar a la función usando asyncio
    try:
        asyncio.run(test_real_arxiv_conversion())
    except Exception as e:
        print(f"[ERROR] Error en la conversion: {e}")
