import asyncio
import logging
import requests
from pathlib import Path
import sys

# Añadir el path de backend para encontrar 'app'
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.document_parser_service import MarkItDownParser

# Configurar logging para ver TODO
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

async def test_direct_image_vlm():
    """
    Test directo para verificar el puente VLM con una imagen real.
    """
    # Usar una imagen garantizada (Logo de Google o similar)
    image_url = "https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_92x30dp.png"
    
    output_dir = Path(__file__).parent / "outputs"
    output_dir.mkdir(exist_ok=True)
    temp_img = output_dir / "test_vlm.png"
    
    print(f"\n[INFO] Descargando imagen de prueba: {image_url}...")
    response = requests.get(image_url)
    temp_img.write_bytes(response.content)
    
    print("[WAIT] Inicializando MarkItDownParser con VLM (Ollama)...")
    parser = MarkItDownParser(
        llm_client="http://localhost:11434/v1", 
        llm_model="gemma4:26b"
    )
    
    print("[RUN] Convirtiendo imagen...")
    # Para imágenes individuales, markitdown.convert() debería llamar al LLM
    # Simulamos el meta
    meta = {"id": "img-test", "title": "Test Image"}
    
    # Intentamos convertir directamente la imagen
    # Usamos el objeto interno md para probar la pureza del puente
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None, lambda: parser.md.convert(str(temp_img))
    )
    
    print("\n[RESULTADO MARKDOWN]:")
    print("-" * 30)
    print(result.markdown)
    print("-" * 30)
    
    if "Description" in result.markdown or "Descripción" in result.markdown:
        print("\n[SUCCESS] El puente VLM funcionó y generó una descripción.")
    else:
        print("\n[WARNING] No se encontró descripción. Verificando logs.")

if __name__ == "__main__":
    asyncio.run(test_direct_image_vlm())
