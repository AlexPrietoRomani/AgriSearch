# Arquitectura de AgriSearch - Chat de Búsqueda Sistemática

Este documento describe la arquitectura, la estructura de archivos y el flujo de llamadas desde que el usuario interactúa con la interfaz de AgriSearch hasta que se genera una respuesta.

## 1. Estructura de Componentes Principales

La aplicación se compone de tres bloques fundamentales:

### **A. Interfaz de Usuario (Frontend: Astro + React + TypeScript + Tailwind)**
Ubicación: `/frontend`

**Páginas Astro** (`src/pages/*.astro`) — ruteo estático base, cada una renderiza un React Island:

| Archivo | Ruta | Componente React |
|---|---|---|
| `index.astro` | `/` | `<Dashboard />` |
| `project.astro` | `/project` | `<ProjectDashboard />` |
| `search.astro` | `/search` | `<SearchWizard />` |
| `screening.astro` | `/screening` | `<ScreeningPage />` |

**Componentes React** (`src/components/*.tsx`) — toda la lógica dinámica:

| Componente | Propósito |
|---|---|
| `Dashboard.tsx` | Página principal: lista de proyectos con crear/eliminar. Modales de confirmación. |
| `ProjectDashboard.tsx` | Detalle del proyecto: editar metadata, historial de búsquedas, historial de revisiones, eliminar con cascada. |
| `SearchWizard.tsx` | Wizard multi-paso: `describe → review_query → searching → results`. Orquesta todo el ciclo de búsqueda AI. |
| `SearchWizardDescribe.tsx` | Paso 1: formulario para tema, idioma, bases de datos, rango de años, modelo LLM. |
| `SearchWizardReview.tsx` | Paso 2: revisar/editar la query booleana generada antes de ejecutar. |
| `SearchWizardSearching.tsx` | Paso 3: spinner animado mientras se ejecuta la búsqueda en paralelo. |
| `SearchWizardResults.tsx` | Paso 4: tabla ordenable de resultados con descarga, reparseo, subida de PDFs, y expansión de abstracts. |
| `ScreeningPage.tsx` | Router de entrada: renderiza `ScreeningSetup` o `ScreeningSession` según el parámetro `?session`. |
| `ScreeningSetup.tsx` | Configuración de sesión: selección de búsquedas, idioma, modelo de traducción, continuar/eliminar existentes. |
| `ScreeningSession.tsx` | Interfaz de cribado artículo por artículo (estilo Rayyan.ai): atajos de teclado, traducción de abstracts, sugerencias AI, vista tarjeta/tabla. |
| `ProgressModal.tsx` | Modal de progreso en tiempo real vía SSE para tareas de fondo (reparseo, enriquecimiento). |

**Cliente API** (`src/lib/api.ts`) — 29 funciones exportadas, todas tipadas con TypeScript. Realiza peticiones `fetch()` HTTP hacia `http://localhost:8000/api/v1`. Maneja errores, parsing JSON, y multipart para subida de PDFs.

### **B. Lógica de Servidor y REST API (Backend: FastAPI + Python + SQLAlchemy)**
Ubicación: `/backend/app`

- **Enrutadores (`api/v1/*.py`)** — 5 módulos de rutas:

| Módulo | Prefijo | Función |
|---|---|---|
| `projects.py` | `/projects` | CRUD de proyectos con conteos de artículos y revisiones. |
| `search.py` | `/search` | Construcción de queries, ejecución multi-DB, descarga de PDFs, reparseo. |
| `screening.py` | `/screening` | Sesiones de cribado, decisiones, sugerencias AI, reranking, traducción, análisis profundo. |
| `events.py` | `/events` | Stream SSE para notificaciones de progreso en tiempo real. |
| `system.py` | `/system` | Estado del sistema y modelos Ollama disponibles. |

- **Servicios (`services/*.py`)** — lógica de negocio pesada:

| Servicio | Responsabilidad principal |
|---|---|
| `search_service.py` | Orquesta búsqueda paralela en 9+ bases, deduplicación DOI + fuzzy title, almacenamiento. |
| `llm_service.py` | Wrapper sobre LiteLLM: generación de queries, traducción, sugerencias de relevancia, análisis de artículos, descripción de imágenes (VLM). |
| `download_service.py` | Descarga paralela de PDFs con rate-limiting, validación magic bytes, pipeline de enriquecimiento automático post-descarga. |
| `query_builder.py` | Construcción determinista (sin LLM) de queries específicas por cada API de base de datos. |
| `pdf_enrichment_service.py` | Coordinación del parseo dual-parser (OpenDataLoader + MarkItDown), extracción de metadatos, publicación de eventos SSE. |
| `document_parser_service.py` | Motor dual de parseo PDF→Markdown: `ParserRouter` selecciona OpenDataLoader (PDFs científicos) o MarkItDown (resto). |
| `vector_service.py` | Gestión de Qdrant: chunking semántico, embeddings nomic-embed-text, indexación y búsqueda vectorial. |
| `active_learning_service.py` | Clasificador TF-IDF + LogisticRegression para priorización de artículos en screening (uncertainty sampling). |
| `summarization_service.py` | Generación de resúmenes estructurados via LLM (objetivo, metodología, resultados, relevancia agrícola). |
| `pdf_parser.py` | Parser Docling legacy para enriquecimiento (ruta alternativa). |

- **Modelos y Schemas (`models/*.py`)**:
  - `project.py`, `screening.py`: SQLAlchemy ORM — tablas SQLite (Project, SearchQuery, Article, ScreeningSession, ScreeningDecision).
  - `schemas.py`: Clases Pydantic para validación estricta de request/response.

### **C. MCP Clients y LLM**
Ubicación: `/backend/app/services/mcp_clients`

AgriSearch se abstrae a través del *Model Context Protocol* para enviar tareas de búsqueda a repositorios científicos. Cada cliente implementa la interfaz específica de cada API:

| Cliente | Base de Datos | Nota |
|---|---|---|
| `openalex_client.py` | OpenAlex | REST API, búsqueda full-text |
| `semantic_scholar_client.py` | Semantic Scholar | REST API, abstracts enriquecidos |
| `arxiv_client.py` | ArXiv | API Atom, formato `all:"term"` |
| `crossref_client.py` | Crossref | REST API, metadatos de citación |
| `core_client.py` | CORE | API v3, acceso abierto |
| `scielo_client.py` | SciELO | REST API, literatura LATAM |
| `redalyc_client.py` | Redalyc | API propia, revistas iberoamericanas |
| `oai_pmh_client.py` | AgEcon + Organic Eprints | OAI-PMH harvesting, post-filtrado local |

**Motor LLM** (`llm_service.py`): Abstracción sobre LiteLLM/Ollama para todas las inferencias:

| Función | Modelo por defecto | Uso |
|---|---|---|
| `generate_search_query()` | Configurable (ej. `deepseek-r1:14b`) | Extraer conceptos PICO + sinónimos AGROVOC |
| `translate_text()` | `llama3.1:8b` | Traducción de abstracts |
| `generate_relevance_suggestion()` | `gemma4:e4b` | Sugerencia few-shot de incluir/excluir |
| `analyze_article_content()` | `gemma4:e4b` | Análisis profundo (resumen, metodología, variables agrícolas) |
| `describe_image_content()` | `gemma4:e4b` | Descripción de figuras vía VLM |

---

## 2. Flujo Completo - "Realizar una Búsqueda"

El SearchWizard gestiona un ciclo de 5 pasos con estados bien definidos: `describe → review_query → searching → results → downloading`. A continuación se detalla cada transición con los archivos, funciones y llamadas API reales.

### Paso 1: Definición del Tema (Frontend — Step `"describe"`)
1. **Componente:** `SearchWizardDescribe.tsx` (renderizado por `SearchWizard.tsx`).
2. **Acción del usuario:** Completa el formulario con:
   - Tema en lenguaje natural (ej. "uso de biofertilizantes en soya para mejorar rendimiento").
   - Áreas agrícolas (multi-select de 10 opciones: general, entomología, fitopatología, etc.).
   - Idioma de búsqueda (`es` / `en`).
   - Modelo LLM (dropdown dinámico de Ollama, default `deepseek-r1:14b`).
   - Bases de datos a consultar (9 opciones, todas seleccionadas por defecto).
   - Rango de años (opcional) y máximo de resultados por fuente (default 50).
3. **Transición:** Al enviar, `SearchWizard` llama `handleGenerateQuery()` que invoca `buildQuery()` de `api.ts`.

### Paso 2: Generación de Query con LLM (Backend)
1. **Endpoint:** `POST /api/v1/search/build-query` → `search.py::build_query()`.
2. **Servicio:** `llm_service.py::generate_search_query(user_input, agri_area, language, year_from, year_to, model)`.
3. **Proceso:**
   - Se inyecta un **prompt de sistema** al LLM que actúa como "bibliotecario agrícola para revisiones sistemáticas".
   - El LLM extrae: `concepts`, `sinonyms` (con terminos AGROVOC), `boolean_query`, `suggested_terms`, `pico_breakdown`, y `explanation`.
   - Temperature: 0.3, max_tokens: 1500, response_format: json_object.
4. **Respuesta:** Objeto `GeneratedQuery` con la tabla PICO interactiva y la query booleana formateada.

### Paso 3: Revisión y Confirmación (Frontend — Step `"review_query"`)
1. **Componente:** `SearchWizardReview.tsx`.
2. **Acción del usuario:**
   - Visualiza la query booleana generada en un editor.
   - Puede **editar manualmente** la query (campo `editedQuery`).
   - Confirma presionando "Ejecutar Búsqueda en Bases de Datos".
3. **Transición:** Llama `handleExecuteSearch()` que invoca `executeSearch()` de `api.ts`.

### Paso 4: Ejecución Paralela y Deduplicación (Backend)
1. **Endpoint:** `POST /api/v1/search/execute` → `search.py::execute_search_endpoint()`.
2. **Servicio:** `search_service.py::execute_search(db, project_id, query, databases, ...)`.
3. **Proceso paso a paso:**
   - **Persistencia inicial:** Crea registro `SearchQuery` en SQLite con el prompt raw y la query generada.
   - **Extracción de conceptos:** `_extract_concepts_from_query()` parsea la query booleana en conceptos limpios (max 10).
   - **Construcción de queries por DB:** `query_builder.py::build_all_queries(concepts, synonyms, databases)` — función **determinista** (sin LLM) que adapta los conceptos a la sintaxis específica de cada API:
     - OpenAlex: `build_openalex_query()` → términos separados por espacio, max 2 sinónimos.
     - ArXiv: `build_arxiv_query()` → formato `all:"término"`, sinónimos con OR, conceptos con AND.
     - Semantic Scholar, Crossref, CORE, SciELO, Redalyc: `build_*_query()` → separados por espacio.
     - AgEcon, Organic Eprints: `build_oaipmh_query()` → harvesting OAI-PMH con post-filtrado local.
   - **Consultas paralelas:** `asyncio.gather()` ejecuta simultáneamente los 9+ MCP clients (`mcp_clients/*_client.py`).
   - **Deduplicación en 3 pasadas:**
     1. DOI exacto: `_normalize_doi()` estandariza y compara.
     2. Título fuzzy: `_is_duplicate_title()` con RapidFuzz ratio >= 0.85.
     3. Contra artículos existentes del proyecto (evita duplicados entre búsquedas).
   - **Almacenamiento:** INSERT de objetos `Article` en SQLite con `project_id` + `search_query_id`.
4. **Respuesta:** JSON `SearchResultsResponse` con `articles`, `counts_by_source`, `adapted_queries`, `duplicates_removed`.

### Paso 4.5: Visualización de Resultados (Frontend — Step `"results"`)
1. **Componente:** `SearchWizardResults.tsx`.
2. **Transición:** El estado `step` cambia a `"results"`, se muestra la tabla de artículos.
3. **Elementos UI:**
   - **Accordion** con el Prompt de Usuario y las Queries Adaptadas por base de datos.
   - **Tabla ordenable** por título, año, fuente, estado de descarga.
   - **Badges de estado** por cada base de datos (colores diferenciados vía `sourceColor()`).
   - **Expansión de abstracts** in-place.
   - **Indicador de duplicados removidos** y conteo por fuente.

### Paso 5: Descarga de PDFs y Enriquecimiento (Backend + Frontend)
1. **Trigger:** El usuario presiona "Descargar PDFs" → `handleDownload()` cambia `step = "downloading"`.
2. **Endpoint:** `POST /api/v1/search/download` → `search.py::download_pdfs()`.
3. **Servicio:** `download_service.py::download_articles(db, project_id, article_ids)`.
4. **Proceso de descarga:**
   - Filtra artículos con `download_status == PENDING` y `open_access_url` no nula.
   - Descarga paralela con `asyncio.gather()` acotada por `Semaphore` (rate-limit configurable).
   - Valida **magic bytes `%PDF`** en el contenido descargado.
   - Nombra archivos: `{año}_{autorApellido}_{títuloSlug}.pdf` → `data/projects/{id}/pdfs/`.
   - Estados posibles: `SUCCESS`, `PAYWALL` (403/401), `FAILED`, `NOT_FOUND`.
5. **Pipeline de enriquecimiento automático** (post-descarga, por cada artículo exitoso):
   - **PDF → Markdown:** `pdf_parser.parse_article()` con ParserRouter (OpenDataLoader para científicos, MarkItDown para otros).
   - **Markdown → LLM:** `llm_service::analyze_article_content()` → extrae `llm_summary`, `relevance_score`, `methodology_type`, `agri_variables` (cultivos, plagas, tratamientos, factores ambientales).
   - **Indexación RAG:** `vector_service.index_article()` → chunking semántico por secciones + embeddings nomic-embed-text → upsert a Qdrant.
6. **Retorno:** El frontend recibe `DownloadProgress` con conteos de éxito/fallo/paywall, y refresca la lista de artículos con `listArticles()`.

---

## 3. Flujo - Historial e Interacción entre Páginas

### Navegación General

El ruteo de Astro sirve las 4 páginas base. Cada una delega en un React Island que gestiona su propio estado:

```
/ (index.astro)  →  <Dashboard />           →  click proyecto  →  /project?id=X
/project          →  <ProjectDashboard />    →  click "BUSQUEDA IA"  →  /search?id=X
                                        →  click "REVISIONES"  →  /screening?id=X&new=true
/search           →  <SearchWizard />        ←  /search?id=X&query_id=Y (histórico)
/screening        →  <ScreeningPage />       →  <ScreeningSetup /> o <ScreeningSession />
```

### Historial de Búsquedas (`ProjectDashboard.tsx`)

1. **Carga:** Al montar, llama `GET /projects/{id}/searches` y `GET /screening/sessions/project/{id}` en paralelo.
2. **Presentación:** Grid de tarjetas de búsqueda. Cada tarjeta muestra:
   - Fecha de creación, prompt original (`raw_input`), total de resultados.
   - Conteo de bases de datos utilizadas y artículos descargados.
   - Artículos no asignados a ninguna sesión de screening.
3. **Acceso a histórico:** Al hacer click en una tarjeta de búsqueda, navega a `/search?id={projectId}&query_id={queryId}`.
4. **Rehidratación en SearchWizard:** El componente detecta el parámetro `?query_id=` en `useEffect()`, salta directamente al `step="results"`, y llama:
   - `getProject(id)` → `GET /projects/{id}` para metadata del proyecto.
   - `listArticles(projectId, 0, 1000, undefined, queryId)` → `GET /search/articles/{projectId}?search_query_id=...` para recuperar los artículos almacenados en SQLite.
5. **Resultado:** El usuario ve exactamente los mismos resultados que generó originalmente, sin re-ejecutar la búsqueda.

### Historial de Revisiones (Screening)

1. **Verificación de elegibilidad:** Antes de crear una nueva revisión, el usuario presiona "REVISIONES" → `ProjectDashboard` llama `GET /screening/eligibility/{projectId}`.
2. **Respuesta del servidor:** `ScreeningEligibility` contiene:
   - `total_downloaded`: artículos con `download_status=SUCCESS`.
   - `assigned_articles`: artículos ya asignados a sesiones existentes.
   - `eligible_articles`: descargados menos asignados (disponibles para nueva sesión).
   - `screening_names`: nombres de sesiones existentes.
3. **Creación de sesión:** Si `eligible_articles > 0`, navega a `/screening?id={projectId}&new=true`.
4. **Setup (`ScreeningSetup.tsx`):**
   - Selecciona qué búsquedas incluir (multi-select con conteos).
   - Configura idioma de lectura y modelo de traducción.
   - Al confirmar: `POST /screening/sessions` con `search_query_ids`, `reading_language`, `translation_model`.
   - El backend ejecuta `enrich_articles_from_pdfs()` (parseo dual si hay PDFs sin Markdown) y crea `ScreeningDecision` para cada artículo no asignado.
5. **Acceso a histórico:** Si ya existe una sesión, se muestra un resumen con Continue/Delete. Click en "Continue" navega a `/screening?id={projectId}&setup_session={sessionId}`.

### Loop de Screening (`ScreeningSession.tsx`)

1. **Carga:** `GET /screening/sessions/{sessionId}` + `GET /screening/sessions/{sessionId}/articles?skip=0&limit=50`.
2. **Interfaz estilo Rayyan.ai:**
   - Vista de tarjeta o tabla (toggle).
   - Abstract traducido bajo demanda: `POST /screening/translate` con `decision_id` y `target_language`.
   - Sugerencia AI por artículo: `GET /screening/sessions/{sessionId}/articles/{articleId}/suggestion`.
   - Atajos de teclado para incluir/excluir/marcar tal vez.
3. **Decisión:** `PUT /screening/decisions/{decisionId}` con `decision` (include/exclude/maybe) y `exclusion_reason` cuando aplica.
4. **Active Learning:** Cada 10 decisiones, el sistema re-entrena el clasificador TF-IDF + LogisticRegression para re-priorizar artículos pendientes (uncertainty sampling). Also disponible vía `POST /screening/sessions/{sessionId}/rerank?mode=uncertainty|most_relevant|balanced`.
5. **Estadísticas en vivo:** `GET /screening/sessions/{sessionId}/stats` → barras de progreso y contadores.

### Eliminaciones Inteligentes

**Eliminar Proyecto** (`DELETE /projects/{id}`):
- **Cascada estricta:** Elimina el directorio completo del proyecto en disco (`shutil.rmtree`) y todos los registros asociados en BD (SearchQuery → Article → ScreeningSession → ScreeningDecision).
- **Modal de confirmación:** `Dashboard.tsx` muestra un modal con advertencia explícita sobre la destrucción de PDFs, datos y revisiones.
- **Post-borrado:** La lista de proyectos se refresca automáticamente y los contadores se recalculan.

**Eliminar Búsqueda** (`DELETE /search/{projectId}/{queryId}`):
- Elimina el `SearchQuery` y todos sus `Article` asociados.
- **Destruye archivos PDF y Markdown locales** del directorio de esa búsqueda.
- Las sesiones de screening que referenciaban esos artículos pierden las referencias (los artículos desaplican de las decisiones).
- `ProjectDashboard` refresca las listas de búsquedas y revisiones post-borrado.

**Eliminar Revisión (Screening Session)** (`DELETE /screening/sessions/{sessionId}`):
- **"Eliminación Segura":** Destruye la sesión y todas sus `ScreeningDecision`, pero **los PDFs descargados no se alteran**.
- Los artículos permanecen en la tabla `Article` y siguen disponibles para ser asignados a una nueva sesión de screening.
- `ProjectDashboard` refresca la lista de revisiones post-borrado.

---

## 4. Diagramas de Computación y Flujos

> Todos los diagramas usan una paleta de colores unificada compatible con fondos blancos y oscuros. Los `classDef` aplicados a los nodos garantizan legibilidad en cualquier tema.

### Paleta de Estilos Global

> Colores mate/strtolower para legibilidad en fondos claros y oscuros.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#5b7fa5', 'primaryTextColor': '#fff', 'lineColor': '#8b8fa3', 'textColor': '#2d3142'}}}%%
graph LR
    classDef frontend fill:#5b7fa5,stroke:#3d5a80,color:#ffffff,stroke-width:2px
    classDef backend fill:#5a8f7b,stroke:#3d6b5e,color:#ffffff,stroke-width:2px
    classDef llm fill:#7e6b99,stroke:#5e4d7a,color:#ffffff,stroke-width:2px
    classDef database fill:#c49a4a,stroke:#9c7a30,color:#ffffff,stroke-width:2px
    classDef external fill:#b85c5c,stroke:#8c3e3e,color:#ffffff,stroke-width:2px
    classDef user fill:#7a7a7a,stroke:#555555,color:#ffffff,stroke-width:2px
    classDef success fill:#5a9e6f,stroke:#3d7a4f,color:#ffffff,stroke-width:2px
    classDef warning fill:#c9a94e,stroke:#9c8230,color:#ffffff,stroke-width:2px
    classDef error fill:#b85c5c,stroke:#8c3e3e,color:#ffffff,stroke-width:2px
    classDef parser_odl fill:#4a7ab5,stroke:#345a8a,color:#ffffff,stroke-width:2px
    classDef parser_mit fill:#7b6199,stroke:#5c4577,color:#ffffff,stroke-width:2px
    classDef common fill:#5a8f6e,stroke:#3d6b52,color:#ffffff,stroke-width:2px

    subgraph Capas
        F["Frontend"]:::frontend
        B["Backend"]:::backend
        L["LLM / IA"]:::llm
        D["Database"]:::database
        E["External"]:::external
    end

    subgraph Estados_y_Parsers
        U["Usuario"]:::user
        S["Success"]:::success
        W["Warning"]:::warning
        ER["Error"]:::error
        ODL["ODL Parser"]:::parser_odl
        MIT["MIT Parser"]:::parser_mit
        C["Common"]:::common
    end
```

---

### 4.1 Arquitectura General del Sistema

A nivel macro, AgriSearch se organiza en 4 capas principales: la interfaz de usuario (Astro + React), el servidor FastAPI con su lógica de negocio, el motor de inferencia local Ollama, y la red de bases de datos científicas externas. SQLite y Qdrant actúan como almacenes locales.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#5b7fa5', 'primaryTextColor': '#fff', 'lineColor': '#8b8fa3', 'textColor': '#2d3142'}}}%%
block
    columns 5

    Frontend["Frontend<br/>Astro + React<br/>TypeScript + Tailwind<br/>Port 4321"]
    space
    Backend["Backend<br/>FastAPI + Python<br/>SQLAlchemy Async<br/>Port 8000"]
    space
    LLM["Procesamiento IA<br/>Ollama Local<br/>LiteLLM Abstraction<br/>Aya / LLaMa3.1 / Qwen"]

    Frontend -- "HTTP JSON REST" --> Backend
    Backend -- "Prompts de Sistema<br/>+ Embeddings" --> LLM

    space:2
    down<[" "]>(down)
    space:2

    SQLite[("SQLite<br/>agrisearch.db<br/>Proyectos + Metadatos<br/>Articulos + Screening")]
    space
    Qdrant[("Qdrant<br/>Vector DB Local<br/>Embeddings por Proyecto<br/>Cosine Similarity")]
    space
    RedCientifica["Red Cientifica<br/>9+ Bases de Datos<br/>OpenAlex / Semantic Scholar<br/>ArXiv / Crossref / CORE"]

    Backend -- "SQLAlchemy<br/>Read/Write" --> SQLite
    Backend -- "Vector Service<br/>nomic-embed-text" --> Qdrant
    Backend -- "Consultas Paralelas<br/>MCP Clients" --> RedCientifica

    classDef frontend fill:#5b7fa5,stroke:#3d5a80,color:#ffffff,stroke-width:2px
    classDef backend fill:#5a8f7b,stroke:#3d6b5e,color:#ffffff,stroke-width:2px
    classDef llm fill:#7e6b99,stroke:#5e4d7a,color:#ffffff,stroke-width:2px
    classDef database fill:#c49a4a,stroke:#9c7a30,color:#ffffff,stroke-width:2px
    classDef external fill:#b85c5c,stroke:#8c3e3e,color:#ffffff,stroke-width:2px
    class Frontend frontend
    class Backend backend
    class LLM llm
    class SQLite,Qdrant database
    class RedCientifica external
```

---

### 4.2 Flujo Macro: Ciclo de Vida de una Revisión Sistemática

Este diagrama muestra los 6 macro-procesos del sistema alineados con las fases de PRISMA 2020. Cada fase se desglosa en micro-procesos en las secciones subsiguientes.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#5b7fa5', 'primaryTextColor': '#fff', 'lineColor': '#8b8fa3', 'textColor': '#2d3142'}}}%%
graph TD
    classDef frontend fill:#5b7fa5,stroke:#3d5a80,color:#ffffff,stroke-width:2px
    classDef backend fill:#5a8f7b,stroke:#3d6b5e,color:#ffffff,stroke-width:2px
    classDef llm fill:#7e6b99,stroke:#5e4d7a,color:#ffffff,stroke-width:2px
    classDef database fill:#c49a4a,stroke:#9c7a30,color:#ffffff,stroke-width:2px
    classDef external fill:#b85c5c,stroke:#8c3e3e,color:#ffffff,stroke-width:2px
    classDef user fill:#7a7a7a,stroke:#555555,color:#ffffff,stroke-width:2px
    classDef success fill:#5a9e6f,stroke:#3d7a4f,color:#ffffff,stroke-width:2px
    classDef warning fill:#c9a94e,stroke:#9c8230,color:#ffffff,stroke-width:2px
    classDef error fill:#b85c5c,stroke:#8c3e3e,color:#ffffff,stroke-width:2px
    classDef parser_odl fill:#4a7ab5,stroke:#345a8a,color:#ffffff,stroke-width:2px
    classDef parser_mit fill:#7b6199,stroke:#5c4577,color:#ffffff,stroke-width:2px
    classDef common fill:#5a8f6e,stroke:#3d6b52,color:#ffffff,stroke-width:2px

    A(["🚀 Inicio: Crear Proyecto"]):::user --> B

    subgraph FASE1 ["📋 FASE 1: IDENTIFICACIÓN"]
        direction TB
        B["Definir Pregunta de Investigación\nEscribir tema en lenguaje natural"]:::frontend
        C["Generar Queries con LLM\nExtracción PICO + sinónimos"]:::llm
        D["Ejecutar Búsqueda Paralela\n9+ bases de datos científicas"]:::external
        E["Deduplicar y Consolidar\nDOI + fuzzy title matching"]:::backend
        B --> C --> D --> E
    end

    E --> F

    subgraph FASE2 ["⬇️ FASE 2: RECOLECCIÓN"]
        direction TB
        F["Descargar Textos Completos\nOpen Access PDFs + Upload manual"]:::backend
        G["Parseo Dual-Parser\nOpenDataLoader + MarkItDown → MD"]:::common
        F --> G
    end

    G --> H

    subgraph FASE3 ["🔍 FASE 3: CRIBADO"]
        direction TB
        H["Configurar Sesión de Screening\nSeleccionar búsquedas + idioma"]:::frontend
        I["Screening Interactivo\nDecisión I/E/M + Atajos teclado"]:::user
        J["Active Learning\nTF-IDF + LogisticRegression"]:::llm
        H --> I --> J
    end

    J --> K

    subgraph FASE4 ["📊 FASE 4: ANÁLISIS"]
        direction TB
        K["Indexación RAG\nChunking semántico → Qdrant"]:::database
        L["Chat RAG + Redacción\nCitación APA estricta"]:::llm
        M["Exploración Bibliométrica\nGrafos citación + temático"]:::common
        K --> L
        K --> M
    end

    L --> N(["📤 Exportar Resultados\nPRISMA Checklist + CSV"]):::success
    M --> N

    style FASE1 fill:#e8edf3,stroke:#5b7fa5,stroke-width:2px,color:#2d3142
    style FASE2 fill:#e8f2ec,stroke:#5a8f7b,stroke-width:2px,color:#2d3142
    style FASE3 fill:#f2efe5,stroke:#c9a94e,stroke-width:2px,color:#2d3142
    style FASE4 fill:#ede5f0,stroke:#7e6b99,stroke-width:2px,color:#2d3142
    style FASE4 fill:#ede5f0,stroke:#7e6b99,stroke-width:2px,color:#2d3142
```

---

### 4.3 Flujo de Búsqueda — Generación de Queries

Micro-proceso desglosado de la Fase 1: Transformar la necesidad del investigador en una estrategia de búsqueda formal. El LLM solo abstrae la matriz de conceptos; **nunca** genera la sintaxis SQL/API directamente.

```mermaid
sequenceDiagram
    box rgb(122,122,122) Investigador
        actor User as Investigador
    end
    box rgb(91,127,165) Frontend
        participant FE as SearchWizard
    end
    box rgb(90,143,123) Backend FastAPI
        participant API as search.py
        participant LLM as llm_service.py
    end

    autonumber

    rect rgb(91,127,165)
        Note over User,FE: Paso 1: Definicion del Tema
        User->>FE: Escribe consulta en lenguaje natural
        Note right of User: Ej: Rendimiento de maiz<br/>con biofertilizantes
        FE->>API: POST /api/v1/search/build-query
    end

    rect rgb(126,107,153)
        Note over API,LLM: Paso 2: Extraccion Semantica con LLM
        API->>LLM: generate_search_query(input, language)
        Note right of LLM: Prompt de Sistema:<br/>Extraer conceptos PICO<br/>+ sinonimos EN/ES<br/>+ terminos AGROVOC
        LLM-->>API: JSON conceptos, sinonimos, PICO, keywords
    end

    rect rgb(91,127,165)
        Note over FE,User: Paso 3: Revision y Aprobacion
        API-->>FE: GeneratedQuery tabla PICO interactiva
        FE->>User: Presenta matriz de conceptos
        User->>FE: Revisa / edita conceptos y presiona Ejecutar
    end
```

---

### 4.4 Flujo de Búsqueda — Ejecución y Deduplicación

Micro-proceso de la Fase 1: Las queries aprobadas se adaptan determinísticamente a la sintaxis de cada API y se ejecutan en paralelo. Luego se fusionan y deduplican los resultados.

```mermaid
sequenceDiagram
    box rgb(90,143,123) Backend Orchestration
        participant BE as search_service.py
        participant QB as query_builder.py
    end
    box rgb(184,92,92) Bases de Datos Cientificas
        participant OA as OpenAlex
        participant SS as Semantic Scholar
        participant AX as ArXiv
        participant CR as Crossref
        participant OT as CORE/SciELO/...
    end
    box rgb(196,154,74) Almacenamiento
        participant DB as SQLite
    end

    autonumber

    rect rgb(90,143,123)
        Note over BE,QB: Paso 4: Adaptacion Determinista de Queries
        BE->>QB: build_all_queries(concepts_json)
        Note right of QB: build_openalex_query()<br/>build_semantic_scholar_query()<br/>build_arxiv_query()<br/>build_crossref_query()<br/>...
        QB-->>BE: adapted_queries = OA, SS, AX, ...
    end

    rect rgb(184,92,92)
        Note over BE,OT: Paso 5: Consultas Paralelas
        par OpenAlex
            BE->>OA: search(adapted_query, limit, year_range)
            OA-->>BE: [Article, Article, ...]
        and Semantic Scholar
            BE->>SS: search(adapted_query, limit)
            SS-->>BE: [Article, Article, ...]
        and ArXiv
            BE->>AX: search(adapted_query, max_results)
            AX-->>BE: [Article, Article, ...]
        and Crossref
            BE->>CR: search(adapted_query)
            CR-->>BE: [Article, Article, ...]
        and Otras bases
            BE->>OT: search(adapted_query)
            OT-->>BE: [Article, Article, ...]
        end
    end

    rect rgb(196,154,74)
        Note over BE,DB: Paso 6: Fusionar y Almacenar
        BE->>BE: Normalizar schema DOI, autores, anio, abstract
        BE->>BE: Deduplicar por DOI exacto
        BE->>BE: Deduplicar fuzzy title RapidFuzz >= 0.85
        BE->>DB: INSERT articulos con project_id + search_query_id
        BE-->>BE: adapted_queries en respuesta JSON
    end
```

---

### 4.5 Flujo de Descarga y Enriquecimiento PDF

Micro-proceso entre Fase 1 y Fase 2: Descarga de textos completos open access y trigger automático del pipeline de enriquecimiento (parseo → LLM → indexación).

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#5b7fa5', 'primaryTextColor': '#fff', 'lineColor': '#8b8fa3', 'textColor': '#2d3142'}}}%%
graph TD
    classDef frontend fill:#5b7fa5,stroke:#3d5a80,color:#ffffff,stroke-width:2px
    classDef backend fill:#5a8f7b,stroke:#3d6b5e,color:#ffffff,stroke-width:2px
    classDef llm fill:#7e6b99,stroke:#5e4d7a,color:#ffffff,stroke-width:2px
    classDef database fill:#c49a4a,stroke:#9c7a30,color:#ffffff,stroke-width:2px
    classDef external fill:#b85c5c,stroke:#8c3e3e,color:#ffffff,stroke-width:2px
    classDef user fill:#7a7a7a,stroke:#555555,color:#ffffff,stroke-width:2px
    classDef success fill:#5a9e6f,stroke:#3d7a4f,color:#ffffff,stroke-width:2px
    classDef warning fill:#c9a94e,stroke:#9c8230,color:#ffffff,stroke-width:2px
    classDef error fill:#b85c5c,stroke:#8c3e3e,color:#ffffff,stroke-width:2px
    classDef parser_odl fill:#4a7ab5,stroke:#345a8a,color:#ffffff,stroke-width:2px
    classDef parser_mit fill:#7b6199,stroke:#5c4577,color:#ffffff,stroke-width:2px
    classDef common fill:#5a8f6e,stroke:#3d6b52,color:#ffffff,stroke-width:2px

    A["Articulos de Busqueda<br/>(DOIs + URLs Open Access)"]:::external --> B{"Tiene URL<br/>Open Access?"}
    B -->|"Si"| C["Descarga asincrona<br/>aiohttp + rate-limit<br/>max 10 req/seg"]:::backend
    B -->|"No"| D["Marcar download_status<br/>= paywall / not_found"]:::warning
    B -->|"Manual"| E["Upload PDF<br/>POST /search/upload-pdf"]:::frontend

    C --> F{"Es PDF<br/>valido?<br/>(magic bytes)"} 
    F -->|"Si"| G["Renombrar: doi_sanitizado<br/>_autor_anio.pdf<br/>data/projects/id/pdfs/"]:::common
    F -->|"No"| H["Marcar failed<br/>+ log error"]:::error

    E --> G
    G --> I["Actualizar BD:<br/>download_status = SUCCESS<br/>local_pdf_path = ruta"]:::database
    D --> I
    H --> I

    I --> J["Trigger Pipeline Enriquecimiento<br/>download_service a pdf_enrichment"]:::llm
    J --> K["Parseo Dual-Parser<br/>(Ver 4.6)"]
    J --> L["Generar Resumen LLM<br/>(summary + relevance)"]
    J --> M["Indexar en Qdrant<br/>(Ver 4.9)"]

    style K fill:#e8edf3,stroke:#4a7ab5,stroke-width:2px,color:#2d3142
    style L fill:#ede5f0,stroke:#7b6199,stroke-width:2px,color:#2d3142
    style M fill:#f0ead5,stroke:#c49a4a,stroke-width:2px,color:#2d3142
```

---

### 4.6 Pipeline de Parseo Dual-Parser

Micro-proceso de Fase 2: Cada documento se procesa con el parser óptimo según su tipo. OpenDataLoader (Java, benchmark #1) para PDFs científicos; MarkItDown (CPU, Microsoft) para todo lo demás. Ambos pipelines convergen en TableFlattener y front-matter YAML.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#5b7fa5', 'primaryTextColor': '#fff', 'lineColor': '#8b8fa3', 'textColor': '#2d3142'}}}%%
graph TD
    classDef frontend fill:#5b7fa5,stroke:#3d5a80,color:#ffffff,stroke-width:2px
    classDef backend fill:#5a8f7b,stroke:#3d6b5e,color:#ffffff,stroke-width:2px
    classDef llm fill:#7e6b99,stroke:#5e4d7a,color:#ffffff,stroke-width:2px
    classDef database fill:#c49a4a,stroke:#9c7a30,color:#ffffff,stroke-width:2px
    classDef external fill:#b85c5c,stroke:#8c3e3e,color:#ffffff,stroke-width:2px
    classDef user fill:#7a7a7a,stroke:#555555,color:#ffffff,stroke-width:2px
    classDef success fill:#5a9e6f,stroke:#3d7a4f,color:#ffffff,stroke-width:2px
    classDef warning fill:#c9a94e,stroke:#9c8230,color:#ffffff,stroke-width:2px
    classDef error fill:#b85c5c,stroke:#8c3e3e,color:#ffffff,stroke-width:2px
    classDef parser_odl fill:#4a7ab5,stroke:#345a8a,color:#ffffff,stroke-width:2px
    classDef parser_mit fill:#7b6199,stroke:#5c4577,color:#ffffff,stroke-width:2px
    classDef common fill:#5a8f6e,stroke:#3d6b52,color:#ffffff,stroke-width:2px

    A(["Documento Descargado"]):::user --> B{"Tipo de<br/>archivo?"}

    B -- "PDF articulo cientifico" --> C["OpenDataLoader PDF Parser<br/>(Layout XY-Cut++, tablas cluster)<br/>Benchmark #1: 0.907"]:::parser_odl
    B -- "DOCX / PPTX / XLSX / HTML" --> D["MarkItDown Parser<br/>(Multi-formato, CPU puro)<br/>~50MB, sin dependencias GPU"]:::parser_mit
    B -- "PDF no-cientifico (fallback)" --> D

    C --> E{"Modo hibrido<br/>activado?"}
    E -- "No" --> F["Conversion local Java JVM<br/>Deteccion layout + tablas"]:::parser_odl
    E -- "Si" --> G["Servidor opendataloader-pdf-hybrid<br/>OCR + Formulas LaTeX<br/>+ Descripciones VLM"]:::parser_odl

    F --> H["Markdown estructurado<br/>con bounding boxes<br/>y tipos semanticos"]:::common
    G --> H

    D --> I{"VLM configurado?<br/>Ollama"}
    I -- "Si" --> J["Conversion + llm_client<br/>Descripciones de imagenes<br/>via Gemma4-Vision"]:::parser_mit
    I -- "No" --> K["Conversion base CPU<br/>Imagenes como placeholders"]:::parser_mit
    J --> L["Genera Markdown"]:::common
    K --> L

    H --> M["TableFlattener<br/>Aplana tablas en oraciones<br/>atomicas para RAG"]:::common
    L --> M

    M --> N["Inyecta front-matter YAML<br/>doi, title, authors, year,<br/>parser_engine, project_id"]:::common
    N --> O["Guarda .md en disco<br/>junto al PDF original"]:::database
    O --> P["Actualizar BD:<br/>local_md_path, parsed_status,<br/>parser_engine, md_length"]:::database
    P --> Q(["Documento.md Enriquecido<br/>Listo para RAG"]):::success
```

---

### 4.7 Flujo de Screening — Setup y Sesión

Micro-proceso de Fase 3: Configuración de la sesión de cribado y el loop interactivo de decisión artículo por artículo, incluyendo traducción de abstracts y.Active Learning.

```mermaid
sequenceDiagram
    box rgb(122,122,122) Investigador
        actor User as Revisor
    end
    box rgb(91,127,165) Frontend
        participant Setup as ScreeningSetup
        participant SS as ScreeningSession
        participant Card as ArticleCard
    end
    box rgb(90,143,123) Backend
        participant API as screening.py
        participant AL as active_learning.py
        participant LLM as llm_service.py
    end
    box rgb(196,154,74) Persistencia
        participant DB as SQLite + Qdrant
    end

    autonumber

    rect rgb(196,154,74)
        Note over User,Setup: Configuracion de Sesion
        User->>Setup: Selecciona busquedas a incluir
        User->>Setup: Configura idioma + modelo traduccion
        Setup->>API: POST /screening/sessions search_ids, language, model
        API->>DB: OUTER JOIN articulos sin asignar a nueva sesion
        API-->>Setup: SessionCreated session_id, article_count
        Setup->>User: Navega a sesion de screening
    end

    rect rgb(91,127,165)
        Note over User,Card: Loop de Screening
        loop Cada articulo pendiente
            SS->>API: GET /sessions/id/articles priorizados
            API->>DB: Consultar articulos ordenados por relevance_score
            API-->>SS: Articulo con abstract + metadata
            SS->>Card: Renderizar tarjeta del articulo

            alt Idioma diferente de original
                SS->>API: POST /screening/translate abstract, target_lang
                API->>LLM: translate_text abstract, lang
                LLM-->>API: Traduccion literal oracion por oracion
                API-->>SS: Abstract traducido cacheado
            end

            Card->>User: Muestra articulo + abstract + traduccion
            User->>Card: Decision: Incluir / Excluir / Tal vez
            Card->>API: PUT /screening/decisions status, motivo
            API->>DB: Registrar decision + timestamp

            alt reviewed_count modulo 10 == 0
                Note over AL,DB: Active Learning cada 10 decisiones
                API->>AL: retrain_model decisiones, embeddings
                AL->>AL: TF-IDF + LogisticRegression
                AL->>AL: Predecir P incluir + incertidumbre
                AL->>DB: Re-priorizar articulos pendientes
            end
        end
    end

    rect rgb(126,107,153)
        Note over API,DB: Estadisticas en Vivo
        SS->>API: GET /sessions/id/stats
        API->>DB: Contar incluidos / excluidos / tal vez / pendientes
        API-->>SS: Stats reviewed, included, excluded, maybe, progress_pct
        SS->>User: Barra de progreso + contadores
    end
```

---

### 4.8 Flujo de Active Learning

Micro-proceso del sistema de cribado: Cada 10 decisiones del usuario, el sistema re-entrena un clasificador ligero para priorizar los artículos con mayor incertidumbre (uncertainty sampling), maximizando la información ganada por cada decisión humana.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#5b7fa5', 'primaryTextColor': '#fff', 'lineColor': '#8b8fa3', 'textColor': '#2d3142'}}}%%
graph TD
    classDef frontend fill:#5b7fa5,stroke:#3d5a80,color:#ffffff,stroke-width:2px
    classDef backend fill:#5a8f7b,stroke:#3d6b5e,color:#ffffff,stroke-width:2px
    classDef llm fill:#7e6b99,stroke:#5e4d7a,color:#ffffff,stroke-width:2px
    classDef database fill:#c49a4a,stroke:#9c7a30,color:#ffffff,stroke-width:2px
    classDef external fill:#b85c5c,stroke:#8c3e3e,color:#ffffff,stroke-width:2px
    classDef user fill:#7a7a7a,stroke:#555555,color:#ffffff,stroke-width:2px
    classDef success fill:#5a9e6f,stroke:#3d7a4f,color:#ffffff,stroke-width:2px
    classDef warning fill:#c9a94e,stroke:#9c8230,color:#ffffff,stroke-width:2px
    classDef error fill:#b85c5c,stroke:#8c3e3e,color:#ffffff,stroke-width:2px
    classDef parser_odl fill:#4a7ab5,stroke:#345a8a,color:#ffffff,stroke-width:2px
    classDef parser_mit fill:#7b6199,stroke:#5c4577,color:#ffffff,stroke-width:2px
    classDef common fill:#5a8f6e,stroke:#3d6b52,color:#ffffff,stroke-width:2px

    A["Pool de Decisiones del Usuario<br/>(Incluidos + Excluidos)<br/>10+ decisiones"]:::user --> B["Vectorizacion TF-IDF<br/>de abstracts decididos"]:::llm
    B --> C["Entrenar LogisticRegression<br/>(scikit-learn)<br/>Balanceo de clases"]:::llm
    C --> D["Predecir P incluir<br/>para cada articulo pendiente"]:::llm
    D --> E["Calcular Incertidumbre<br/>P incluir - 0.5 < epsilon"]:::common

    E --> F{"Estrategia<br/>de ranking?"}
    F -->|"Uncertainty<br/>explorar"| G["Priorizar: mayor<br/>incertidumbre primero<br/>(articulos dudosos)"]:::warning
    F -->|"Most Relevant<br/>explotar"| H["Priorizar: mayor<br/>P incluir primero<br/>(articulos prometedores)"]:::success
    F -->|"Balanced<br/>por defecto"| I["Combinacion ponderada<br/>incertidumbre x relevancia"]:::backend

    G --> J["Re-ordenar lista<br/>de articulos pendientes"]:::database
    H --> J
    I --> J

    J --> K["Actualizar sugerencias<br/>en Frontend<br/>(banner visual + confianza)"]:::frontend
    K --> L["Usuario decide<br/>(posiblemente influenciado)"]:::user
    L --> M["Comparar sugerencia<br/>vs decision real<br/>accuracy tracking"]:::common
    M --> A

    style A fill:#e8edf3,stroke:#7a7a7a,stroke-width:2px,color:#2d3142
    style J fill:#f0ead5,stroke:#c49a4a,stroke-width:2px,color:#2d3142
    style K fill:#e8f2ec,stroke:#5a8f7b,stroke-width:2px,color:#2d3142
```

---

### 4.9 Flujo de Indexación RAG

Micro-proceso de Fase 4: Los Markdown procesados de artículos incluidos se fragmentan semánticamente por secciones, se enriquecen con metadatos de procedencia y se vectorizan para habilitar recuperación semántica precisa en el chat RAG.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#5b7fa5', 'primaryTextColor': '#fff', 'lineColor': '#8b8fa3', 'textColor': '#2d3142'}}}%%
graph TD
    classDef frontend fill:#5b7fa5,stroke:#3d5a80,color:#ffffff,stroke-width:2px
    classDef backend fill:#5a8f7b,stroke:#3d6b5e,color:#ffffff,stroke-width:2px
    classDef llm fill:#7e6b99,stroke:#5e4d7a,color:#ffffff,stroke-width:2px
    classDef database fill:#c49a4a,stroke:#9c7a30,color:#ffffff,stroke-width:2px
    classDef external fill:#b85c5c,stroke:#8c3e3e,color:#ffffff,stroke-width:2px
    classDef user fill:#7a7a7a,stroke:#555555,color:#ffffff,stroke-width:2px
    classDef success fill:#5a9e6f,stroke:#3d7a4f,color:#ffffff,stroke-width:2px
    classDef warning fill:#c9a94e,stroke:#9c8230,color:#ffffff,stroke-width:2px
    classDef error fill:#b85c5c,stroke:#8c3e3e,color:#ffffff,stroke-width:2px
    classDef parser_odl fill:#4a7ab5,stroke:#345a8a,color:#ffffff,stroke-width:2px
    classDef parser_mit fill:#7b6199,stroke:#5c4577,color:#ffffff,stroke-width:2px
    classDef common fill:#5a8f6e,stroke:#3d6b52,color:#ffffff,stroke-width:2px

    A["Markdown Procesados<br/>(articulos incluidos en screening)<br/>Sub-fase 2.0"]:::common --> B["Leer .md + parsear<br/>front-matter YAML<br/>(doi, authors, year, section)"]:::backend
    B --> C["Detectar secciones<br/>por headers ##/###<br/>Markdown structure-aware"]:::backend
    C --> D{"Seccion ><br/>800 tokens?"}
    D -- "Si" --> E["Subdividir por parrafos<br/>con overlap 100 tokens<br/>(rango dinamico 300-800)"]:::backend
    D -- "No" --> F["Chunk = seccion completa"]:::backend

    E --> G["Inyectar metadatos<br/>a cada chunk:<br/>doi, section, element_type,<br/>page_range, project_id"]:::common
    F --> G

    G --> H["Generar embeddings<br/>nomic-embed-text<br/>768 dimensiones<br/>via Ollama"]:::llm
    H --> I["Almacenar en Qdrant<br/>Coleccion: project_uuid<br/>Cosine Similarity"]:::database
    I --> J["Crear Indice BM25<br/>complementario<br/>rank_bm25"]:::backend
    J --> K["Configurar Hybrid Retriever<br/>Reciprocal Rank Fusion<br/>(vector + BM25)"]:::backend
    K --> L["Test de Sanidad<br/>Query prueba a chunk<br/>debe estar en top-5"]:::success
    L --> M(["Pipeline RAG listo<br/>para Chat Fase 3"]):::success
```

---

### 4.10 Modelo de Datos — Diagrama ER

Las 5 entidades core del sistema SQLite. Todas usan `UUIDv4` como clave primaria para garantizar aislamiento entre proyectos concurrentes.

```mermaid
erDiagram
    Project ||--o{ SearchQuery : "tiene"
    Project ||--o{ ScreeningSession : "tiene"
    SearchQuery ||--o{ Article : "produce"
    ScreeningSession ||--o{ ScreeningDecision : "genera"
    Article ||--o{ ScreeningDecision : "evalúa"

    Project {
        uuid id PK
        string name
        string description
        string agri_area
        string language
        string llm_model
        datetime created_at
    }

    SearchQuery {
        uuid id PK
        uuid project_id FK
        string raw_input
        string generated_query
        json databases_used
        json adapted_queries
        int total_results
        datetime created_at
    }

    Article {
        uuid id PK
        uuid project_id FK
        uuid search_query_id FK
        string doi
        string title
        json authors
        int year
        string journal
        text abstract
        string source_db
        string download_status
        string local_pdf_path
        string local_md_path
        string parsed_status
        float relevance_score
        text llm_summary
    }

    ScreeningSession {
        uuid id PK
        uuid project_id FK
        string name
        string objective
        json search_query_ids
        string reading_language
        string translation_model
        int reviewed_count
        int included_count
        int excluded_count
        int maybe_count
        datetime created_at
    }

    ScreeningDecision {
        uuid id PK
        uuid session_id FK
        uuid article_id FK
        string status
        string exclusion_reason
        string reviewer_note
        text translated_abstract
        int display_order
        datetime decided_at
    }
```

---

### 4.11 Diagrama de Componentes y Deployment

Vista técnica de los servicios y puertos que componen la infraestructura local de AgriSearch.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#5b7fa5', 'primaryTextColor': '#fff', 'lineColor': '#8b8fa3', 'textColor': '#2d3142'}}}%%
graph LR
    classDef frontend fill:#5b7fa5,stroke:#3d5a80,color:#ffffff,stroke-width:2px
    classDef backend fill:#5a8f7b,stroke:#3d6b5e,color:#ffffff,stroke-width:2px
    classDef llm fill:#7e6b99,stroke:#5e4d7a,color:#ffffff,stroke-width:2px
    classDef database fill:#c49a4a,stroke:#9c7a30,color:#ffffff,stroke-width:2px
    classDef external fill:#b85c5c,stroke:#8c3e3e,color:#ffffff,stroke-width:2px
    classDef user fill:#7a7a7a,stroke:#555555,color:#ffffff,stroke-width:2px
    classDef success fill:#5a9e6f,stroke:#3d7a4f,color:#ffffff,stroke-width:2px
    classDef warning fill:#c9a94e,stroke:#9c8230,color:#ffffff,stroke-width:2px
    classDef error fill:#b85c5c,stroke:#8c3e3e,color:#ffffff,stroke-width:2px
    classDef parser_odl fill:#4a7ab5,stroke:#345a8a,color:#ffffff,stroke-width:2px
    classDef parser_mit fill:#7b6199,stroke:#5c4577,color:#ffffff,stroke-width:2px
    classDef common fill:#5a8f6e,stroke:#3d6b52,color:#ffffff,stroke-width:2px

    subgraph Usuario ["🖥️ Estación del Usuario"]
        direction TB
        Browser["Navegador Web<br/>Chrome / Firefox / Edge"]:::user
    end

    subgraph FrontendLayer ["🌐 Frontend — localhost:4321"]
        direction TB
        Astro["Astro SSR<br/>Pages: index, project,<br/>search, screening"]:::frontend
        React["React Islands<br/>Dashboard, SearchWizard,<br/>ScreeningSession"]:::frontend
    end

    subgraph BackendLayer ["⚙️ Backend — localhost:8000"]
        direction TB
        FastAPI["FastAPI Server<br/>5 route modules:<br/>projects, search, screening,<br/>events, system"]:::backend
        Services["Servicios Core<br/>search_service, llm_service,<br/>query_builder, download_service,<br/>vector_service, active_learning"]:::backend
        MCPClients["MCP Clients (9)<br/>OpenAlex, Semantic Scholar,<br/>ArXiv, Crossref, CORE,<br/>SciELO, Redalyc, OAI-PMH"]:::external
        Parsers["Dual Parser<br/>OpenDataLoader (Java)<br/>MarkItDown (Python)"]:::common
    end

    subgraph Infrastructure ["💾 Almacenamiento & IA"]
        direction LR
        subgraph DataLayer ["Almacenamiento Local"]
            SQLite[("SQLite<br/>agrisearch.db")]:::database
            Qdrant[("Qdrant<br/>Vector DB<br/>localhost:6333")]:::database
            PDFs["📁 data/projects/{id}/<br/>pdfs/ + parsed/"]:::database
        end

        subgraph LLLayer ["Inferencia Local"]
            Ollama["Ollama<br/>localhost:11434"]:::llm
            Models["Modelos:<br/>llama3.1:8b (chat)<br/>aya:8b (multilingual)<br/>nomic-embed-text (768d)<br/>gemma4:e4b (VLM)"]:::llm
        end
    end

    Browser <-->|"HTTP/REST"| Astro
    Astro <--> React
    React <-->|"fetch() API"| FastAPI
    FastAPI <--> Services
    Services <--> MCPClients
    Services <--> Parsers
    Services <--> SQLite
    Services <--> Qdrant
    Services <--> PDFs
    Services <-->|"LiteLLM"| Ollama
    Ollama --- Models
```

---

### 4.12 Estados del Proyecto — Flujo PRISMA

Diagrama de estados que muestra cómo evoluciona un proyecto a través del flujo PRISMA 2020, desde la identificación inicial hasta la inclusión final.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#5b7fa5', 'primaryTextColor': '#fff', 'lineColor': '#8b8fa3', 'textColor': '#2d3142'}}}%%
graph TD
    classDef frontend fill:#5b7fa5,stroke:#3d5a80,color:#ffffff,stroke-width:2px
    classDef backend fill:#5a8f7b,stroke:#3d6b5e,color:#ffffff,stroke-width:2px
    classDef llm fill:#7e6b99,stroke:#5e4d7a,color:#ffffff,stroke-width:2px
    classDef database fill:#c49a4a,stroke:#9c7a30,color:#ffffff,stroke-width:2px
    classDef external fill:#b85c5c,stroke:#8c3e3e,color:#ffffff,stroke-width:2px
    classDef user fill:#7a7a7a,stroke:#555555,color:#ffffff,stroke-width:2px
    classDef success fill:#5a9e6f,stroke:#3d7a4f,color:#ffffff,stroke-width:2px
    classDef warning fill:#c9a94e,stroke:#9c8230,color:#ffffff,stroke-width:2px
    classDef error fill:#b85c5c,stroke:#8c3e3e,color:#ffffff,stroke-width:2px
    classDef parser_odl fill:#4a7ab5,stroke:#345a8a,color:#ffffff,stroke-width:2px
    classDef parser_mit fill:#7b6199,stroke:#5c4577,color:#ffffff,stroke-width:2px
    classDef common fill:#5a8f6e,stroke:#3d6b52,color:#ffffff,stroke-width:2px

    subgraph F1 ["📋 IDENTIFICACIÓN"]
        A["📋 Proyecto<br/>Creado"]:::user -->|"Crear búsquedas"| B["🔍 Búsquedas<br/>Generadas"]:::frontend
        B -->|"Ejecutar search"| C["📚 Artículos<br/>Identificados<br/>(N de cada base)"]:::external
        C -->|"Deduplicación"| D["🔄 Duplicados<br/>Removidos<br/>(N únicos)"]:::warning
    end

    subgraph F2 ["⬇️ RECOLECCIÓN"]
        D -->|"Descargar PDFs"| E["⬇️ Texto Completo<br/>Descargado<br/>(N con PDF)"]:::backend
        D -->|"Paywall/Error"| F["❌ Sin Texto<br/>Completo"]:::error
        E -->|"Parseo MD"| G["📄 Markdown<br/>Procesado<br/>(N con MD)"]:::common
    end

    subgraph F3 ["🔍 CRIBADO"]
        G -->|"Extracción y Traducción"| G2["🌐 Resumen y Palabras Clave<br/>(En idioma preferido)"]:::llm
        G2 -->|"Screening"| H["🔍 Screeneados<br/>(Incluidos / Excluidos)"]:::llm
        H -->|"Incluidos"| I["✅ Artículos<br/>Incluidos<br/>(Base del conocimiento)"]:::success
        H -->|"Excluidos"| J["❌ Artículos<br/>Excluidos<br/>(con motivo PRISMA)"]:::error
    end

    subgraph F4 ["📊 ANÁLISIS"]
        I -->|"Indexar RAG"| K["🧠 Qdrant<br/>Vectorizado<br/>(listo para Chat)"]:::database
        K -->|"Chat RAG"| L["💬 Chat + Redacción<br/>Citación APA"]:::llm
        K -->|"Explorar"| M["🕸️ Grafos de Citación<br/>y Relación Temática"]:::common
        I -->|"Exportar"| N["📤 PRISMA<br/>Checklist + CSV"]:::success
        L --> N
        M --> N
    end

    style A fill:#e8e8e8,stroke:#7a7a7a,stroke-width:2px,color:#2d3142
    style C fill:#f5e0e0,stroke:#b85c5c,stroke-width:2px,color:#2d3142
    style D fill:#f2efe5,stroke:#c9a94e,stroke-width:2px,color:#2d3142
    style I fill:#e8f5ed,stroke:#5a9e6f,stroke-width:2px,color:#2d3142
    style J fill:#f5e0e0,stroke:#b85c5c,stroke-width:2px,color:#2d3142
    style K fill:#f0ead5,stroke:#c49a4a,stroke-width:2px,color:#2d3142
    style N fill:#e8f5ed,stroke:#5a9e6f,stroke-width:2px,color:#2d3142
```
