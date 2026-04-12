import asyncio
import sys
import os
from pathlib import Path

# Fix unicode output in windows console
sys.stdout.reconfigure(encoding='utf-8')

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.append(str(backend_path))

from app.services.document_parser_service import MarkItDownParser
from app.services.pdf_enrichment_service import process_and_enrich_pdf
from app.db.database import async_session_factory
from app.models.project import Article
from sqlalchemy import select

async def test_single_pdf_conversion():
    print("🚀 Iniciando test de conversión simple...")
    
    # 1. Buscar un PDF real existente (Se usa uno muy grande para testear el chunking de Docling)
    pdf_path = Path(r"C:\Users\ALEX\Github\AgriSearch\backend\data\projects\Investigacion_CNN_vs_Vision_Attention\Busqueda_1\descargas\2025_Hanyu_Multimodal_Learning_for_Visual_Perception_and_Robo.pdf")
    
    if not pdf_path.exists():
        print(f"❌ Error: El PDF no existe en {pdf_path}")
        return

    print(f"📂 PDF encontrado: {pdf_path.name}")

    # 2. Inicializar el parser
    try:
        parser = MarkItDownParser()
        print("✅ MarkItDownParser inicializado con éxito.")
    except Exception as e:
        print(f"❌ Error al inicializar MarkItDownParser: {e}")
        return

    # 3. Simular un objeto Article para SQLAlchemy
    async with async_session_factory() as db:
        # Intentamos obtener un artículo real de la base de datos para que tenga contexto
        stmt = select(Article).where(Article.local_pdf_path.isnot(None)).limit(1)
        result = await db.execute(stmt)
        article = result.scalar_one_or_none()
        
        if not article:
            print("⚠️ No hay artículos en la DB, creando uno temporal en memoria...")
            article = Article(
                id="test-uuid",
                title="Test Manual PDF",
                doi="10.test/123",
                project_id="test-project",
                local_pdf_path=str(pdf_path)
            )
        else:
            print(f"📄 Usando artículo real de la DB: {article.title}")
            # Forzamos la ruta al PDF que sabemos que existe
            article.local_pdf_path = str(pdf_path)

        # 4. Ejecutar la conversión
        print("⏳ Ejecutando parse_pdf (esto puede tardar unos segundos)...")
        try:
            # Simulamos meta-data
            meta = {
                "id": article.id,
                "title": article.title,
                "doi": article.doi,
                "authors": article.authors or "Test Author",
                "year": article.year or 2025,
                "journal": article.journal or "Test Journal",
                "source_database": "test"
            }
            
            final_md = await parser.parse_pdf(pdf_path, meta)
            
            print("✅ ¡Conversión completada!")
            print(f"📝 Longitud del Markdown generado: {len(final_md)} caracteres")
            
            # Guardar resultado temporal
            output_test = Path(__file__).parent / "test_output.md"
            output_test.write_text(final_md, encoding="utf-8")
            print(f"💾 Resultado guardado en: {output_test}")
            
            # Mostrar los primeros 500 caracteres
            print("\n--- VISTA PREVIA ---")
            print(final_md[:500] + "...")
            print("--------------------\n")
            
        except Exception as e:
            print(f"❌ Error durante la conversión: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_single_pdf_conversion())
