# CLAUDE.md

Este archivo proporciona orientación a Claude Code (claude.ai/code) cuando trabaja con el código de este repositorio.

## Comandos de Desarrollo

### Backend (FastAPI)

- **Configurar entorno**: `cd backend && uv sync`
- **Ejecutar servidor**: `cd backend && uv run uvicorn app.main:app --reload`
- **Ejecutar tests**: `uv run pytest` (desde el directorio raíz del proyecto)
- **Ejecutar un test específico**: `uv run pytest tests/unit/test_search_clients.py`
- **Migración/inicialización de base de datos**: `cd backend && uv run python create_tables.py`
- **Verificar esquema de la base de datos**: `cd backend && uv run python dump_schema.py`
- **Verificar integridad de la base de datos**: `cd backend && uv run python check_db.py`

### Frontend (Astro + React)

- **Instalar dependencias**: `cd frontend && npm install`
- **Ejecutar servidor de desarrollo**: `cd frontend && npm run dev`
- **Construir para producción**: `cd frontend && npm run build`

## Resumen de la Arquitectura

AgriSearch es una aplicación de dos capas diseñada para revisiones sistemáticas de literatura siguiendo las directrices PRISMA 2020.

### Estructura del Backend (`/backend`)
Construido con **FastAPI**, el backend gestiona orchestraciones complejas entre bases de datos científicas, LLMs locales (vía Ollama) y almacenamiento vectorial.

- **`app/api/v1/`**: Endpoints de la API REST organizados por dominio:
    - `projects.py`: Gestión de proyectos de investigación y metadatos.
    - `search.py`: Construcción de consultas (vía LLM), ejecución en múltiples bases de datos y descarga de PDFs.
    - `screening.py`: Flujos de trabajo de cribado (screening) compatibles con PRISMA, seguimiento de decisiones y traducción de resúmenes.
    - `events.py`: Sistema de eventos en tiempo real para notificaciones de progreso.
    - `system.py`: Endpoints de administración y monitoreo del sistema.
- **`app/services/`**: Lógica de negocio central:
    - `search_service.py`: Orquesta búsquedas en OpenAlex, Semantic Scholar, ArXiv, etc.
    - `download_service.py`: Gestiona la recuperación asíncrona de PDFs.
    - `llm_service.py`: Interfaz para generar consultas de búsqueda y extraer conceptos usando Ollama/LiteLLM.
    - `document_parser_service.py`: Conversión avanzada de PDF a Markdown con Docling, OCR, VLM para imágenes y table flattening.
    - `pdf_enrichment_service.py`: Coordinación del procesamiento masivo de PDFs, indexación vectorial y extracción de metadatos.
    - `pdf_parser.py`: Parser PDFs legacy con soporte básico de Docling y OCR.
    - `active_learning_service.py`: Sistema de aprendizaje activo para mejorar el screening.
    - `summarization_service.py`: Generación de resúmenes de documentos.
    - `vector_service.py`: Indexación y búsqueda en Qdrant (RAG).
    - `query_builder.py`: Construcción de consultas optimizadas.
    - `mcp_clients/`: Clientes especializados para interactuar con fuentes externas de datos científicos.
- **`app/core/`**: Configuración central, seguridad y utilidades core.
- **`app/utils/`**: Funciones utilitarias compartidas.
- **`app/models/`**: Modelos SQLAlchemy para SQLite y esquemas Pydantic para validación de la API.
- **`app/db/`**: Lógica de conexión e inicialización de la base de datos.

### Estructura del Frontend (`/frontend`)
Una aplicación basada en **Astro** con un enfoque de renderizado híbrido (SSR para velocidad/SEO, React para componentes interactivos).

- **`src/lib/api.ts`**: Cliente TypeScript centralizado para todas las interacciones con la API del backend.
- **`src/components/`**: Componentes interactivos basados en React (ej. visor de PDF, tarjetas de cribado, formularios de búsqueda).
- **`src/pages/`**: Rutas de Astro que definen las vistas de la aplicación (Lista de proyectos, Interfaz de búsqueda, Panel de cribado).
- **Estilos**: Utiliza **Tailwind CSS** para un estilo responsivo y basado en utilidades.

### Flujo de Datos
1. **Fase de Búsqueda**: Entrada del usuario → LLM (Ollama) → Consulta Booleana → Llamadas a múltiples APIs → Almacenamiento en SQLite/Qdrant.
2. **Fase de Procesamiento PDF→MD**:
   - **Conversión estructural**: Docling procesa PDFs en chunks (10 páginas) con preservación de tablas y fórmulas.
   - **OCR**: Activado para PDFs escaneados (`do_ocr = True`).
   - **Análisis de imágenes (VLM)**: Modelos multimodales (llama3.2-vision o gemma4) describen imágenes científicas, filtrando contenido decorativo.
   - **Table Flattening**: Conversión de tablas Markdown a oraciones descriptivas con contexto (autor, año, título).
   - **Front-matter YAML**: Inyección de metadatos bibliográficos estructurados.
   - **Indexación vectorial**: Contenido Markdown indexado en Qdrant para búsqueda semántica RAG.
3. **Fase de Cribado (Screening)**: Documentos enriquecidos → Decisión del usuario (Incluir/Excluir) → Actualización de la base de datos → Feedback para active learning.

### Stack Tecnológico Clave
- **Backend**: FastAPI, SQLAlchemy, SQLite, Pydantic Settings
- **Frontend**: Astro 5.x, React 19.x, Tailwind CSS 4.x
- **LLMs/VLMs**: Ollama (gemma4:e4b, llama3.2-vision), LiteLLM
- **Procesamiento PDF**: Docling (IBM), OCR integrado, pypdf
- **Vector DB**: Qdrant (RAG semántico)
- **Embeddings**: nomic-embed-text-v2-moe

<!-- autoskills:start -->

Summary generated by `autoskills`. Check the full files inside `.claude/skills`.

## Accessibility (a11y)

Audit and improve web accessibility following WCAG 2.2 guidelines. Use when asked to "improve accessibility", "a11y audit", "WCAG compliance", "screen reader support", "keyboard navigation", or "make accessible".

- `.claude/skills/accessibility/SKILL.md`
- `.claude/skills/accessibility/references/A11Y-PATTERNS.md`: Practical, copy-paste-ready patterns for common accessibility requirements. Each pattern is self-contained and linked from the main [SKILL.md](../SKILL.md).
- `.claude/skills/accessibility/references/WCAG.md`

## Design Thinking

Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, artifacts, posters, or applications (examples include websites, landing pages, dashboards, React components, HTML/CSS layouts, or when styling/beaut...

- `.claude/skills/frontend-design/SKILL.md`

## SEO optimization

Optimize for search engine visibility and ranking. Use when asked to "improve SEO", "optimize for search", "fix meta tags", "add structured data", "sitemap optimization", or "search engine optimization".

- `.claude/skills/seo/SKILL.md`

<!-- autoskills:end -->
