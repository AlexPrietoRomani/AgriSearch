"""
Archivo: test_conversion_manual.py
Modificación: 2026-05-06
Autor: Alex Prieto

Descripción:
Script de prueba manual para validar la conversión de documentos PDF a Markdown.
Permite ejecutar el pipeline de parseo sobre un archivo específico sin necesidad 
de levantar toda la infraestructura de pruebas automatizadas.

Acciones Principales:
    - Validación de la existencia de archivos PDF de prueba.
    - Inicialización de los motores de parseo (MarkItDown).
    - Simulación de objetos de base de datos (Article) para el contexto del parser.
    - Ejecución de la conversión y guardado del resultado en archivos temporales.

Entradas / Dependencias:
    - Un archivo PDF real en la ruta especificada.
    - `MarkItDownParser` del servicio de documentos.

Ejemplo de Uso:
    python tests/backend/test_conversion_manual.py
"""

import asyncio
import sys
import traceback
from pathlib import Path

from sqlalchemy import select

# Configurar la salida de la consola para soportar caracteres Unicode en Windows
sys.stdout.reconfigure(encoding='utf-8')

# Agregar el directorio backend al path para resolver importaciones
backend_path = Path(__file__).parent.parent / "backend"
sys.path.append(str(backend_path))

from app.services.document_parser_service import MarkItDownParser
from app.db.database import async_session_factory
from app.models.project import Article


async def test_single_pdf_conversion():
    """
    Ejecuta una prueba de conversión simple sobre un PDF real.

    Busca un PDF en el sistema de archivos, lo procesa con MarkItDown y guarda
    el Markdown resultante en el directorio 'outputs'.
    """
    print("🚀 Iniciando test de conversión simple...")
    
    # 1. Buscar un PDF real existente (Se usa uno representativo para el test)
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
            output_dir = Path(__file__).parent / "outputs"
            output_dir.mkdir(exist_ok=True)
            output_test = output_dir / "test_output.md"
            output_test.write_text(final_md, encoding="utf-8")
            print(f"💾 Resultado guardado en: {output_test}")
            
            # Mostrar los primeros 500 caracteres
            print("\n--- VISTA PREVIA ---")
            print(final_md[:500] + "...")
            print("--------------------\n")
            
        except Exception as e:
            print(f"❌ Error durante la conversión: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_single_pdf_conversion())
