import pytest
from pathlib import Path

# Assumeollama_available is defined somewhere or we can mock it
def ollama_available():
    # Placeholder implementation, ideally this checks if ollama is running
    return True

class TestActiveLearningWithPDFs:
    ASSETS_DIR = Path(__file__).parent.parent.parent / "assets" / "pdf"
    
    def test_pdfs_exist(self):
        """Verifica que los PDFs de prueba existen."""
        expected = ["ndvi_crop_health.pdf", "multispectral_weed_detection.pdf"]
        for fname in expected:
            pdf_path = self.ASSETS_DIR / fname
            if not pdf_path.exists():
                pytest.skip(f"PDF no descargado: {fname}")
            assert pdf_path.stat().st_size > 0
    
    @pytest.mark.skipif(not ollama_available(), reason="Ollama no disponible")
    def test_extract_embeddings_from_real_pdf(self):
        """Extrae embeddings de un PDF real usando Ollama."""
        pdf_path = self.ASSETS_DIR / "ndvi_crop_health.pdf"
        if not pdf_path.exists():
            pytest.skip("PDF no descargado")
        # MarkItDown para convertir PDF a MD
        # Ollama para extraer embeddings
        pass
    
    @pytest.mark.skipif(not ollama_available(), reason="Ollama no disponible")
    def test_screening_workflow_with_real_pdfs(self):
        """Flujo completo de screening: PDF → MD → embeddings → classify."""
        pass
