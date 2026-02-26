# Documentación Técnica - AgriSearch

Este documento contiene el registro de cambios funcionales, decisiones técnicas, flujos de datos relevantes y posibles errores para mantener la trazabilidad de la aplicación AgriSearch.

---

## Registro de Cambios y Funcionalidades

### Búsqueda y Obtención de PDFs (Fase 1)
- **Extracción Inteligente:** Ejecuta queries a OpenAlex, Semantic Scholar y Arxiv, deduplica e inserta en SQLite.
- **Descarga Múltiple Open Access:** El servicio `download_service.py` obtiene automáticamente los PDFs vía requests asíncronas de las URLs enlazadas, los guarda en `data/projects/{id}/pdfs` y los nombra automáticamente usando la convención `[Año]_[PrimerAutor]_[Slug_Titulo].pdf`.
- **Subida Manual (Upload):** Endpoint `POST /search/upload-pdf/{article_id}`. Para los artículos que están bloqueados por un paywall, el usuario puede subir localmente su archivo PDF desde el dashboard de resultados. El archivo se enlaza directamente a su base de datos.
- **API Response:** `ArticleResponse` incluye `local_pdf_path` para que el frontend pueda mostrar el nombre del archivo local en la tabla de resultados.

### Screening (Cribado PRISMA) (Fase 2)

#### Reglas de Negocio
- **Solo artículos con PDF** (`download_status = SUCCESS`) se incluyen en una sesión de screening.
- **1 sesión activa por proyecto.** Se retorna HTTP 409 si se intenta crear una segunda.
- **Identidad de sesión:** Cada sesión tiene `name` (requerido) y `goal` (opcional) para darle contexto descriptivo.

#### Endpoints Relevantes
| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/screening/sessions` | POST | Crea sesión (solo PDFs, max 1 por proyecto) |
| `/screening/sessions/{session_id}` | GET | Detalle de sesión |
| `/screening/sessions/{session_id}` | DELETE | Elimina sesión y todas sus decisiones (cascade) |
| `/screening/sessions/project/{project_id}` | GET | Lista sesiones del proyecto |
| `/screening/sessions/{session_id}/articles` | GET | Artículos en la sesión con sus decisiones |
| `/screening/decisions/{decision_id}` | PUT | Actualizar decisión (include/exclude/maybe) |
| `/screening/translate` | POST | Traducir abstract vía LLM |
| `/screening/enrich/{project_id}` | POST | Enriquecimiento pre-screening desde PDFs |

#### Flujo del Frontend (`ScreeningSetup.tsx`)
1. Al entrar a `/screening?id=X`, se verifica si hay sesión existente.
2. **Si hay sesión:** Muestra tarjeta resumen con estadísticas → Continuar o Eliminar.
3. **Si no hay:** Formulario de creación con nombre, objetivo, selección de búsquedas, idioma y modelo.
4. Al crear, ejecuta enriquecimiento automático (PyMuPDF) y luego crea la sesión (filtrada solo PDFs).

#### Pantalla Previa `ScreeningSetup`
- Permite elegir qué consultas integrar en el proceso actual y con qué modelo traducir los resúmenes.
- **Enriquecimiento del PDF:** Antes de crear una sesión formal de screening iterativo, el sistema escanea la carpeta `/pdfs/` usando PyMuPDF:
    1. Trata de encontrar emparejamientos por DOI o coincidencia parcial en nombre de archivo.
    2. Modifica la DB y extrae el Abstract directamente del archivo PDF en caso de que la búsqueda original no incluyera uno.
    3. Extrae palabras clave (keywords).

#### Proceso Interactivo (`ScreeningSession`)
Interfaz para "Incluir", "Excluir", o marcar como "Tal vez" (Maybe). Autores largos se truncan con `formatAuthors` y resúmenes se traducen con Ollama local.

#### Intención Futura: Multi-persona
> En versiones posteriores se permitirá tener múltiples sesiones para que varias personas trabajen simultáneamente en el screening de un mismo proyecto, cada una con sus artículos asignados. Por ahora, la restricción de 1 sesión simplifica el flujo.

---

## Dependencias Críticas
- **PyMuPDF**: Necesario en el backend para la extracción limpia de texto de archivos PDF durante la fase pre-screening. (`pip install PyMuPDF`).
- **Ollama**: Requiere tener en ejecución instancias de modelos LLM. Por ejemplo, `aya-expanse` como opción multilingüe óptima de 8B.

## Modelos LLM Sugeridos (Ollama)
1. **Aya Expanse (`aya-expanse`)** — Recomendado. Modelo 8B de Cohere optimizado para 23 idiomas. Excelente para traducciones EN↔ES/PT.
2. **Llama 3.1 8B (`llama3.1:8b`)** — Rendimiento general sólido.
3. **Qwen 2.5 7B (`qwen2.5:7b`)** — Alternativa rápida y eficiente.

> **Nota:** El modelo `aya-23:8b` fue reemplazado por `aya-expanse` al verificar que ofrece mejor calidad de traducción multilingüe.

## UI/UX Global
- **Modo claro/oscuro:** Toggle global persistente (localStorage) en la barra de navegación, disponible en todas las páginas.

---

*Nota: Este documento debe ser actualizado iterativamente al realizar modificaciones importantes, en cumplimiento con el flujo `update-documentation.md`.*
