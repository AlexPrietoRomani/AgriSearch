# Documentación Técnica - AgriSearch

Este documento contiene el registro de cambios funcionales, decisiones técnicas, flujos de datos relevantes y posibles errores para mantener la trazabilidad de la aplicación AgriSearch.

## Registro de Cambios y Funcionalidades

### Búsqueda y Obtención de PDFs (Fase 1)
- **Extracción Inteligente:** Ejecuta queries a OpenAlex, Semantic Scholar y Arxiv, deduplica e inserta en SQLite.
- **Descarga Múltiple Open Access:** El servicio `download_service.py` obtiene automáticamente los PDFs vía requests asíncronas de las URLs enlazadas, los guarda en `data/projects/{id}/pdfs` y los nombra automáticamente usando la convención `[Año]_[PrimerAutor]_[Slug_Titulo].pdf`.
- **Subida Manual (Upload):** Nuevo endpoint `POST /search/upload-pdf/{article_id}`. Para los artículos que están bloqueados por un paywall, el usuario puede subir localmente su archivo PDF desde el dashboard de resultados. El archivo se enlaza directamente a su base de datos.

### Screening (Cribado Pragma) (Fase 2)
- **Pantalla Previa `ScreeningSetup`:** Permite elegir qué consultas integrar en el proceso actual y con qué modelo traducir los resúmenes.
- **Enriquecimiento del PDF:** Antes de crear una sesión formal de screening iterativo, el sistema escanea la carpeta `/pdfs/` usando PyMuPDF:
    1. Trata de encontrar emparejamientos por DOI o coincidencia parcial en nombre de archivo (si se cargó desde otra vía).
    2. Modifica la DB y extrae el Abstract directamente del archivo PDF en caso de que la búsqueda original no incluyera uno.
    3. Extrae palabras clave (keywords).
- **Proceso Interactívo (`ScreeningSession`):** Interfaz para "Incluir", "Excluir", o marcar como "Tal vez" (Maybe). Autores largos se truncan con `formatAuthors` y resúmenes se traducen con Ollama local.

## Dependencias Críticas
- **PyMuPDF**: Necesario en el backend para la extracción limpia de texto de archivos PDF durante la fase pre-screening. (`pip install PyMuPDF`).
- **Ollama**: Requiere tener en ejecución instancias de modelos LLM. Por ejemplo, `aya-expanse` como opción multilingüe óptima de 8B.

## Modelos LLM Sugeridos recomendados localmente
1. **Llama 3.1 8B (`llama3.1:8b`)**: Rendimiento general.
2. **Aya Expanse (`aya-expanse`)**: Excelente modelo base 8B para traducciones y procesamiento multilingüe, creado por Cohere.
3. **Qwen 2.5 7B (`qwen2.5:7b`)**: Muy rápido y eficiente.

---

*Nota: Este documento debe ser actualizado iterativamente por el asistente virtual al realizar modificaciones importantes, en cumplimiento con el flujo `update-documentation.md`.*
