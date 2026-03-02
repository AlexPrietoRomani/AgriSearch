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

### 4.1 Arquitectura General del Sistema

A nivel macro, AgriSearch funciona como un monolito divido en Frontend y Backend que se comunican de forma asíncrona, apoyándose de un LLM local e integrándose a la red científica a través de un patrón de conectores MCP (Model Context Protocol).

```mermaid
graph TD
    subgraph Client [Navegador del Usuario]
        UI[UI Components Astro/React]
        API_C[API Client fetch/REST]
    end

    subgraph Servidor [Backend FastAPI]
        Routes[Enrutadores API v1]
        Logic[Servicios Core & Lógica]
        DB[(Base de Datos SQLite)]
    end

    subgraph LLM_Provider [Procesamiento IA Local]
        Ollama[Motor Ollama]
        Models[Modelos: Aya, LLaMa3.1, Qwen]
    end

    subgraph Red_Cientifica [Fuentes Externas]
        OA[OpenAlex]
        SS[Semantic Scholar]
        ArXiv[ArXiv]
        Otras[Otras 6 Bases...]
    end

    UI <-->|HTTP JSON| API_C
    API_C <-->|Peticiones REST| Routes
    Routes <--> Logic
    Logic <-->|Lectura/Escritura SQLAlchemy| DB
    Logic <-->|Prompts de Sistema| Ollama
    Ollama --- Models
    Logic <-->|Adaptadores Deterministas| OA
    Logic <-->|Consultas Paralelas| SS
    Logic <-->|Requests Asíncronos| ArXiv
    Logic <--> Otras
```

### 4.2 Flujo Interno de la "Búsqueda" (Search Generation & Execution)

Este flujo expone qué pasa en la Fase 1. El motor no delega la construcción del lenguaje de la base de datos al LLM para prevenir fallos impredecibles de sintaxis; en su lugar, el modelo solo abstrae la matriz de conceptos, y adaptadores deterministas construyen el literal de búsqueda.

```mermaid
sequenceDiagram
    actor User as Investigador
    participant FE as Interfaz de Búsqueda
    participant BE as FastAPI Backend
    participant LLM as Ollama Local
    participant QBuild as Constructor de Queries
    participant MCP as MCP Clients (Scrapers/APIs)
    participant DB as SQLite

    User->>FE: Describe el tema (Ej. "Rendimiento de maíz con biofertilizantes")
    FE->>BE: POST /search/build-query
    BE->>LLM: Inyecta texto a Prompt Sistémico (Extracción Semántica)
    LLM-->>BE: Devuelve JSON {conceptos, sinónimos, estructura PICO}
    BE-->>FE: Presenta Tabla PICO interactiva
    
    User->>FE: Revisa/Edita matriz y presiona "Ejecutar"
    FE->>BE: POST /search/execute
    
    BE->>DB: Guarda registro de Intención de Búsqueda
    BE->>QBuild: build_all_queries() basada en conceptos matriciales
    QBuild-->>BE: JSON Adaptado {OpenAlex: "(maize) AND (biofertilizers)", Arxiv: "all:maize..."}
    
    par Consultas Multihilo concurrentes
        BE->>MCP: Client OpenAlex
        BE->>MCP: Client Semantic Scholar
        BE->>MCP: Client ArXiv ...etc
    end
    MCP-->>BE: Listas crudas de Artículos
    
    BE->>BE: Algoritmos de Fusión (Deduplicación por DOI y RapidFuzz Titles)
    BE->>DB: Almacena Resultados Depurados
    
    BE-->>FE: Devuelve colección limpia
    FE->>User: Renderiza Panel con Tabla de Artículos
```

### 4.3 Flujo del Sistema de "Revisiones" (Screening & Eligibility)

Flujo para la Fase 2 (Cribado PRISMA). Subraya la comprobación de **artículos elegibles** y la arquitectura de **enriquecimiento local del PDF**.

```mermaid
sequenceDiagram
    actor User as Revisor
    participant FE as Project Dashboard
    participant API as FastAPI Backend
    participant DB as SQLite
    participant PyMu as Motor PDF (PyMuPDF)
    participant LLM as Ollama Local

    User->>FE: Click en botón "Revisiones"
    FE->>API: GET /screening/eligibility (Valida seguridad)
    API->>DB: Cuenta (Descargas Totales) vs (Artículos ya asignados a otra sesión)
    DB-->>API: {elegibles, asignados}
    API-->>FE: Devuelve Conteo
    
    alt elegibles == 0
        FE->>User: Bloqueo: "⚠️ No hay artículos libres para evaluar."
    else elegibles > 0
        FE->>User: Muestra Modal de Configuración (Nueva Sesión)
        User->>FE: Define Modelo IA, Idioma de Lectura y Búsquedas Origen
        FE->>API: POST /screening/sessions
        
        Note over API,PyMu: Fase 1: Enriquecimiento Offline Inteligente
        API->>PyMu: Extrae textos de archivos PDF .pdf en disco
        PyMu-->>API: Regex Parsing (Abstracts y Keywords perdidas de APIs abiertas)
        API->>DB: Guarda nuevos hallazgos en Metadata de Artículos
        
        Note over API,DB: Fase 2: Configurando Sesión Concurrentes
        API->>DB: Crea Objeto `ScreeningSession`
        API->>DB: Crea fila `ScreeningDecision` (SÓLO para artículos NO asignados en otras sesiones)
        DB-->>API: ID de la Sesión
        API-->>FE: Redirecciona al Panel de Cribado interactivo
        
        FE->>User: Interfaz estilo Rayyan (Left: Artículos, Right: Detalles)
        
        loop Por cada lectura / evaluación
            User->>FE: Click (Incluir ✅ / Excluir ❌)
            FE->>API: PUT /decisions/{id} (Guarda estado)
            
            opt Abstract Ilegible
                User->>FE: Click "Traducir Abstract"
                FE->>API: POST /screening/translate
                API->>LLM: Prompt estricto de traducción literal
                LLM-->>API: Abstract traducido
                API->>DB: Persiste texto en ScreeningDecision
                API-->>FE: Refleja nuevo texto al investigador
            end
        end
    end
```
