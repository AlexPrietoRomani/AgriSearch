# Arquitectura de AgriSearch - Chat de Búsqueda Sistemática

Este documento describe la arquitectura, la estructura de archivos y el flujo de llamadas desde que el usuario interactúa con la interfaz de AgriSearch hasta que se genera una respuesta.

## 1. Estructura de Componentes Principales

La aplicación se compone de tres bloques fundamentales:

### **A. Interfaz de Usuario (Frontend: Astro + React + TypeScript + Tailwind)**
Ubicación: `/frontend`
- **Astro (`src/pages/*.astro`)**: Administra las páginas estáticas y el ruteo base de la app. Por ejemplo, `index.astro`, `project.astro`, `search.astro`, `screening.astro`.
- **Componentes React (`src/components/*.tsx`)**: Proveen toda la experiencia visual e interacciones dinámicas. 
  - *ProjectList.tsx / ProjectDashboard.tsx / SearchWizard.tsx / ScreeningApp.tsx*.
- **Cliente API (`src/lib/api.ts`)**: Archivo central de TypeScript que realiza todas las peticiones `fetch()` HTTP hacia el backend y tipa firmemente los datos de entrada/salida.

### **B. Lógica de Servidor y REST API (Backend: FastAPI + Python + SQLAlchemy)**
Ubicación: `/backend/app`
- **Enrutadores (`api/v1/*.py`)**: Son las vías de entrada. Definen los `endpoints` REST como `/projects`, `/search`, `/screening`. Extraen parámetros y llaman a la respectiva capa de servicio.
- **Servicios (`services/*.py`)**: Donde sucede toda la lógica de negocio pesada, como procesamiento, orquestamiento de llamadas a LLM y limpieza de datos.
- **Modelos y Schemas (`models/*.py`)**: 
  - *project.py*, *screening.py*: Es donde SQLAlchemy define las tablas SQLite.
  - *schemas.py*: Colección de clases Pydantic que aseguran la validación estricta de la información bidireccional cliente-servidor API REST.

### **C. MCP Clients y LLM**
Ubicación: `/backend/app/services/mcp_clients`
- AgriSearch se abstrae a través del *Model Context Protocol* para poder mandar tareas especializadas de búsqueda y recuperación a repositorios científicos u otras herrmaientas conectadas.
- **`Search Build LLM` (`query_builder.py`)**: Para procesar el prompt inicial que describe lo que quiere el usuario y convertirlo a representaciones booleanas/semánticas.

---

## 2. Flujo Completo - "Realizar una Búsqueda"

Para ejemplificar, se describe detalladamente qué pasa tras bambalinas cuando un usuario ingresa y crea una búsqueda AI.

### Paso 1: Seleccionar el Proyecto (Frontend)
1. **Archivo Relevante:** `frontend/src/pages/index.astro` 
2. **Acción:** El usuario hace click en crear o en abrir un proyecto. 
3. **Redirección:** Entramos a `/project.astro -> <ProjectDashboard />`.

### Paso 2: Ir a "Búsqueda AI" 
1. **Acción:** Click en "Búsqueda AI", nos lleva a `frontend/src/pages/search.astro`. Que a su vez renderiza `<SearchWizard />`.
2. **Estado Inicial:** `step="describe"`. 

### Paso 3: Definición del Prompt (Generar Queries)
1. **Archivo Relevante:** `frontend/src/components/SearchWizard.tsx`
2. **Acción:** El usuario escribe su consulta en lenguaje natural (ej., "uso de biofertilizantes en soya") y hace click en "Generar Sugerencias".
3. **Llamada API (`api.ts`):** Envia un POST a `buildQuery(data)` hacia la ruta base del backend `POST /api/v1/search/build-query`.

### Paso 4: Backend construye la Búsqueda
1. **Entrada Backend:** `backend/app/api/v1/search.py` (Endpoint `/build-query`).
2. **Capa Funcional (`services/search_service.py`):**
   - El servicio llama a `generate_search_concepts(user_input, language)`.
   - Esto inyecta un *Prompt de Sistema* a un modelo LLM (Ollama) para extraer conceptos clave y descomponer la petición en PICO.
3. **Respuesta:** Retorna el objeto `GeneratedQuery` de vuelta al UI.

### Paso 5: Vista Previa y Confirmación (Frontend)
1. **Estado (`SearchWizard.tsx`):** Pasa al `step="review"`.
2. **Acción:** El usuario verifica e incluso puede cambiar las BD a consultar (Redalyc, arXiv, OpenAlex, Semantic Scholar, etc.). Luego da click en "Ejecutar Búsqueda en Bases de Datos".

### Paso 6: Orquestar las Bases de Datos 
1. **Llamada (`executeSearch` en `api.ts`):** Apunta al POST `/api/v1/search/execute`.
2. **Capa de Servicio Orquestadora (`search_service.py` -> `execute_search`):**
   - Guarda el `SearchQuery` inicial en la base de datos (junto con el string del prompt).
   - A través de la función de `build_all_queries`, transforma la búsqueda general a las sintaxis requeridass de cada Base de Datos seleccionada (JSON final almacenado en el registro).
   - Genera Tareas Asíncronas (`asyncio.gather`) y paraleliza las llamadas a cada Base de datos a través de los diversos *MCP/Clients* situados en `backend/app/services/mcp_clients/*_client.py`.

### Paso 7: Procesamiento y Unificación 
1. **Regreso de Tareas:** Todos los *clients* retornan su lista de artículos.
2. **Filtrado Centralizado:**
   - Estandarización de `doi` e IDs unicos.
   - Eliminación de Duplicados intrafuente e inter-fuente mediante coincidencia estricta y comparativa difusa de títulos (Fuzzy Match / RapidFuzz).
   - Construcción y almacenamiento de objetos SQLAlchemy clase `Article` en la Base de Datos asociadas al Proyecto (`project_id`) y Búsqueda (`search_query_id`).
3. **Retorno GUI:** FastAPI responde el objeto JSON del esquema de Respuesta SearchResult.

### Paso 8: Visualizar y Descargar (Resultados)
1. **Estado:** `SearchWizard` pasa a `step="results"` y muestra `<SearchWizardResults />`.
2. **Nuevos Cambios Incorporados:** 
   - Se pinta un panel tipo Accordion con el **Prompt de Usuario** y las **Queries Adaptadas** específicas que fueron tiradas por comando a cada Base de Datos gracias a los atributos `prompt_used` y `adapted_queries` proveidos.
3. **Acción Descarga (`downloadArticles`):** La descarga extrae todos los URLs abiertos/DOIs de sus fuentes Open Access y guarda localmente dentro del directorio del proyecto respetando metadatos.

---

## 3. Flujo - Historial e Interacción entre Páginas

- **Historial de Búsquedas (`ProjectDashboard.tsx`):**
  - Solicita `GET /projects/{id}/searches`.
  - Presenta un panel de tarjetas. Al hacer click en una, viaja a la URL `/search?query_id=ABC`.
  - El `<SearchWizard />` captura ese ID en el `useEffect()`, cambia directamente a `results` e infla el estado recuperando todo desde SQLite.
- **Historial de Revisiones (`ProjectDashboard.tsx` -> Screening):**
  - Solicita `GET /screening/eligibility/{project_id}` antes de permitir crear una revisión. El servidor valida artículos disponibles cruzando datos con sesiones activas.
  - Al hacer click en "Revisiones", el usuario puede crear una nueva (`new=true`) si cumple elegibilidad.
  - Igual metodología en acceso histórico (`setup_session=...`). La presentación dinámica redirige hacia `<ScreeningApp />` en otra URL aislada por ID de sesión.
- **Eliminaciones Inteligentes (`DELETE /projects`, `DELETE /search`, o `DELETE /screening/session`):**
  - **Eliminar Proyecto/Búsqueda**: Se orquestan en Cascada estricta (Cascading Delete). Al eliminar desde el Dashboard, emerge un **Modal Interactivo de Alerta** pidiendo confirmación explícita para evitar errores destructivos. Un `SearchQuery` o proyecto eliminado erradica su metadata en BD (incluyendo forzados a artículos huérfanos), y mediante hooks y servicios **se destruyen todos los archivos PDF locales** asociados junto con los registros de Screening que dependían de ellos. El sistema re-calcula sumas dinámicamente post-borrado.
  - **Eliminar Revisión (Screening Session)**: "Eliminación Segura". Se destruye la revisión y todas sus decisiones de inclusión/exclusión, pero **los PDFs descargados no sufren ninguna alteración**. Permanecen listos y disponibles subyacentemente en su carpeta sanitizada o para ser asignados a una nueva revisión concurrente.

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
graph TD
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
graph TD
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

    style K fill:#e8edf3,stroke:#4a7ab5,stroke-width:2px
    style L fill:#ede5f0,stroke:#7b6199,stroke-width:2px
    style M fill:#f0ead5,stroke:#c49a4a,stroke-width:2px
```

---

### 4.6 Pipeline de Parseo Dual-Parser

Micro-proceso de Fase 2: Cada documento se procesa con el parser óptimo según su tipo. OpenDataLoader (Java, benchmark #1) para PDFs científicos; MarkItDown (CPU, Microsoft) para todo lo demás. Ambos pipelines convergen en TableFlattener y front-matter YAML.

```mermaid
graph TD
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
graph TD
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

    style A fill:#e8edf3,stroke:#7a7a7a,stroke-width:2px
    style J fill:#f0ead5,stroke:#c49a4a,stroke-width:2px
    style K fill:#e8f2ec,stroke:#5a8f7b,stroke-width:2px
```

---

### 4.9 Flujo de Indexación RAG

Micro-proceso de Fase 4: Los Markdown procesados de artículos incluidos se fragmentan semánticamente por secciones, se enriquecen con metadatos de procedencia y se vectorizan para habilitar recuperación semántica precisa en el chat RAG.

```mermaid
graph TD
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
graph LR
    subgraph Usuario ["🖥️ Estación del Usuario"]
        Browser["Navegador Web\nChrome / Firefox / Edge"]:::user
    end

    subgraph FrontendLayer ["🌐 Frontend — localhost:4321"]
        Astro["Astro SSR\nPages: index, project,\nsearch, screening"]:::frontend
        React["React Islands\nDashboard, SearchWizard,\nScreeningSession"]:::frontend
    end

    subgraph BackendLayer ["⚙️ Backend — localhost:8000"]
        FastAPI["FastAPI Server\n5 route modules:\nprojects, search, screening,\nevents, system"]:::backend
        Services["Servicios Core\nsearch_service, llm_service,\nquery_builder, download_service,\nvector_service, active_learning"]:::backend
        MCPClients["MCP Clients (9)\nOpenAlex, Semantic Scholar,\nArXiv, Crossref, CORE,\nSciELO, Redalyc, OAI-PMH"]:::external
        Parsers["Dual Parser\nOpenDataLoader (Java)\nMarkItDown (Python)"]:::common
    end

    subgraph DataLayer ["💾 Almacenamiento Local"]
        SQLite[("SQLite\nagrisearch.db")]:::database
        Qdrant[("Qdrant\nVector DB\nlocalhost:6333")]:::database
        PDFs["📁 data/projects/{id}/\npdfs/ + parsed/"]:::database
    end

    subgraph LLLayer ["🧠 Inferencia Local"]
        Ollama["Ollama\nlocalhost:11434"]:::llm
        Models["Modelos:\nllama3.1:8b (chat)\naya:8b (multilingual)\nnomic-embed-text (768d)\ngemma4:e4b (VLM)"]:::llm
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
graph LR
    A["📋 Proyecto\nCreado"]:::user -->|"Crear búsquedas"| B["🔍 Búsquedas\nGeneradas"]:::frontend
    B -->|"Ejecutar search"| C["📚 Artículos\nIdentificados\n(N de cada base)"]:::external
    C -->|"Deduplicación"| D["🔄 Duplicados\nRemovidos\n(N únicos)"]:::warning
    D -->|"Descargar PDFs"| E["⬇️ Texto Completo\nDescargado\n(N con PDF)"]:::backend
    D -->|"Paywall/Error"| F["❌ Sin Texto\nCompleto"]:::error
    E -->|"Parseo MD"| G["📄 Markdown\nProcesado\n(N con MD)"]:::common
    G -->|"Screening"| H["🔍 Screeneados\n(Incluidos / Excluidos)"]:::llm
    H -->|"Incluidos"| I["✅ Artículos\nIncluidos\n(Base del conocimiento)"]:::success
    H -->|"Excluidos"| J["❌ Artículos\nExcluidos\n(con motivo PRISMA)"]:::error
    I -->|"Indexar RAG"| K["🧠 Qdrant\nVectorizado\n(listo para Chat)"]:::database
    K -->|"Chat RAG"| L["💬 Chat + Redacción\nCitación APA"]:::llm
    K -->|"Explorar"| M["🕸️ Grafos de Citación\ny Relación Temática"]:::common
    I -->|"Exportar"| N["📤 PRISMA\nChecklist + CSV"]:::success
    L --> N
    M --> N

    style A fill:#e8e8e8,stroke:#7a7a7a,stroke-width:2px
    style C fill:#f0ead5,stroke:#c49a4a,stroke-width:2px
    style D fill:#f0ead5,stroke:#c49a4a,stroke-width:2px
    style I fill:#e8f2ec,stroke:#5a8f7b,stroke-width:2px
    style J fill:#f5e0e0,stroke:#b85c5c,stroke-width:2px
    style K fill:#ede5f0,stroke:#7e6b99,stroke-width:2px
    style N fill:#e8f2ec,stroke:#5a8f7b,stroke-width:2px
```
