# AgriSearch: Plataforma de Búsqueda Sistemática y Asistente de Investigación Agrícola basada en PRISMA 2020

---

## 1. Propósito General

Desarrollar una aplicación web local, modular, segura y orientada a Clean Code, especializada en **ciencias agrícolas** (ensayos en campo, biotecnología, entomología, fitopatología, breeding, agricultura de precisión, entre otros). La plataforma asistirá a investigadores en la realización de revisiones sistemáticas siguiendo rigurosamente la metodología **PRISMA 2020** (Page et al., 2021).

La herramienta integrará tres capacidades clave mediante una arquitectura desacoplada (Frontend Astro + Backend FastAPI):

1. **Búsqueda Sistemática Exhaustiva** — Identificación y descarga masiva de artículos científicos desde múltiples bases de datos (OpenAlex, Semantic Scholar, ArXiv, Web) con generación de queries semánticas asistidas por LLM.
2. **Screening Inteligente Estilo Rayyan** — Cribado semi-automático con Active Learning donde el LLM aprende de las decisiones del usuario para priorizar artículos, siguiendo el flujo de PRISMA 2020 desde la identificación hasta la inclusión.
3. **Chat RAG Conversacional con Citación APA Estricta** — Interfaz de diálogo sobre el corpus incluido, con capacidad de asistir en la redacción académica de TFMs, tesis y artículos científicos.

Todo gestionado **por proyectos independientes**, permitiendo al usuario llevar simultáneamente 2, 3 o más revisiones completamente aisladas entre sí (cada una con su propia base de datos vectorial, historial de screening y chat).

---

## 2. Estructura de Carpetas del Código Fuente

```text
Chat_busqueda_sistematica/
│
├── frontend/                          # Aplicación Astro (UI)
│   ├── src/
│   │   ├── layouts/                   # Layouts base
│   │   │   └── MainLayout.astro       # Layout principal (✅)
│   │   ├── pages/                     # Rutas de la app
│   │   │   ├── index.astro            # Dashboard principal — listado de proyectos (✅)
│   │   │   ├── project.astro          # Dashboard individual por proyecto (✅)
│   │   │   ├── search.astro           # Wizard de búsqueda sistemática (✅)
│   │   │   └── screening.astro        # Screening / Cribado (⏳ pendiente)
│   │   ├── components/                # Componentes React
│   │   │   ├── Dashboard.tsx          # Gestor de proyectos (✅)
│   │   │   ├── ProjectDashboard.tsx   # Panel de detalles e historial de cada proyecto (✅)
│   │   │   ├── SearchWizard.tsx       # Asistente multi-paso para búsqueda — orchestrator (✅)
│   │   │   ├── SearchWizardDescribe.tsx # Paso 1: Descripción de la búsqueda (✅)
│   │   │   ├── SearchWizardReview.tsx   # Paso 2: Revisión de la query generada (✅)
│   │   │   ├── SearchWizardSearching.tsx# Paso 3: Interfaz de búsqueda en curso (✅)
│   │   │   ├── SearchWizardResults.tsx  # Paso 4: Resultados con tabla, LaTeX y descarga (✅)
│   │   │   ├── ScreeningSetup.tsx     # Config screening: selección búsquedas + idioma (⏳)
│   │   │   ├── ScreeningSession.tsx   # Sesión de cribado artículo por artículo (⏳)
│   │   │   ├── ScreeningArticleCard.tsx # Tarjeta de artículo con abstract + traducción (⏳)
│   │   │   ├── ScreeningStats.tsx     # Panel lateral: progreso y contadores (⏳)
│   │   │   └── ScreeningListView.tsx  # Vista tabla alternativa de todos los artículos (⏳)
│   │   ├── styles/                    # CSS global y Tailwind
│   │   │   └── global.css
│   │   └── lib/                       # Utilidades y cliente API
│   │       └── api.ts
│   │   └── react-latex-next.d.ts      # Declaración de tipos para LaTeX (✅)
│   ├── public/                        # Assets estáticos
│   ├── astro.config.mjs
│   └── package.json
│
├── backend/                           # Servidor Python (FastAPI)
│   ├── app/
│   │   ├── main.py                    # Punto de entrada FastAPI
│   │   ├── core/
│   │   │   ├── config.py              # Variables de entorno y settings (Pydantic Settings)
│   │   │   ├── security.py            # Rate limiting, CORS, sanitización de inputs
│   │   │   └── logging_config.py      # Configuración centralizada de logs
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── projects.py        # CRUD de proyectos
│   │   │   │   ├── search.py          # Endpoints de búsqueda sistemática
│   │   │   │   ├── screening.py       # Endpoints de screening (clasificación)
│   │   │   │   ├── chat.py            # Endpoints de chat RAG
│   │   │   │   ├── documents.py       # Upload/download de PDFs
│   │   │   │   └── writing.py         # Endpoints de asistencia de redacción
│   │   │   └── deps.py                # Dependencias inyectadas (DB sessions, etc.)
│   │   ├── services/
│   │   │   ├── search_service.py      # Lógica de búsqueda (MCP clients, dedup)
│   │   │   ├── download_service.py    # Descarga de PDFs con rate-limit y validación DOI
│   │   │   ├── screening_service.py   # Active Learning + clasificación LLM
│   │   │   ├── rag_service.py         # Pipeline RAG (chunking, embedding, retrieval)
│   │   │   ├── chat_service.py        # Orquestación de chat con citaciones APA
│   │   │   ├── writing_service.py     # Análisis de borradores y feedback
│   │   │   ├── llm_service.py         # Wrapper sobre LiteLLM (abstracción de modelos)
│   │   │   └── mcp_clients/
│   │   │       ├── openalex_client.py
│   │   │       ├── semantic_scholar_client.py
│   │   │       ├── arxiv_client.py
│   │   │       └── browser_client.py
│   │   ├── models/
│   │   │   ├── project.py             # Modelo de Proyecto (SQLAlchemy / Pydantic)
│   │   │   ├── article.py             # Modelo de Artículo con metadatos
│   │   │   ├── screening_decision.py  # Modelo de decisiones de screening
│   │   │   └── chat_history.py        # Modelo de historial de chat
│   │   ├── db/
│   │   │   ├── database.py            # Engine y Session de SQLAlchemy
│   │   │   └── migrations/            # Alembic migrations
│   │   └── utils/
│   │       ├── pdf_parser.py          # Extracción de texto de PDFs
│   │       ├── doi_validator.py       # Validación y resolución de DOIs
│   │       ├── apa_formatter.py       # Formateador de citas APA 7ma ed.
│   │       ├── deduplication.py       # Algoritmos de deduplicación fuzzy
│   │       └── csv_exporter.py        # Exportador CSV/Excel compatible PRISMA
│   ├── requirements.txt
│   └── alembic.ini
│
├── data/                              # Datos locales POR PROYECTO
│   └── projects/
│       └── {project_uuid}/
│           ├── raw/                   # CSVs de búsquedas crudas
│           ├── pdfs/                  # Artículos descargados
│           ├── processed/             # Datos filtrados post-screening
│           └── exports/               # Reportes exportados
│
├── vector_db/                         # Qdrant colecciones POR PROYECTO
│   └── {project_uuid}/               # Colección aislada por proyecto
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── docs/
│   └── plan_a_seguir.md               # Este documento
│
├── .agents/
│   └── workflows/                     # Skills y workflows para desarrollo
│
├── .gitignore
├── README.md
└── docker-compose.yml                 # (Opcional) Qdrant + Ollama containerizados
```

---

## 3. Estructura de la Plataforma (Diseño de UI/UX)

### 3.1 Dashboard Principal (`/` → `index.astro` → `Dashboard.tsx`)

Pantalla de inicio donde se listan todos los **Proyectos de Revisión** del usuario. Cada proyecto es una revisión sistemática independiente.

**Estado actual (✅ Implementado):**
- **Crear Nuevo Proyecto:** Formulario con nombre, descripción, selección múltiple de áreas agrícolas (entomología, fitopatología, breeding, biotecnología, agricultura de precisión, ciencias del suelo, agronomía, malherbología, otro), e idioma (ES/EN).
- **Tarjetas de Proyecto:** Cada tarjeta muestra el nombre del proyecto, descripción, áreas agrícolas, y conteo exacto de **artículos totales** y **artículos revisados** (gracias a subconsultas SQL dinámicas).
- **Eliminar Proyecto (Seguridad en Cascada):** Interfaz modal superpuesta (backdrop blur) que pide confirmación estricta visual impidiendo el borrado accidental por desajustes gráficos nativos. Inicia la eliminación escalonada en SQL que erradica y limpia bases de datos de decisiones y PDFs físicos huérfanos locales.
- **Acceso directo:** Click en tarjeta navega a `/project?id=X`.

### 3.2 Vista de Proyecto (`/project?id=X` → `project.astro` → `ProjectDashboard.tsx`)

Consola individual del proyecto con la información y acciones disponibles.

**Estado actual (✅ Implementado):**
- **Cabecera editable:** Nombre, descripción y áreas agrícolas editables inline (modo vista / modo edición).
- **Historial de Búsquedas:** Tabla listando todas las `SearchQuery` del proyecto (fecha, input original, query generada, BDs usadas, total resultados, duplicados removidos). Cada fila es clicable y redirige al Wizard con los resultados precargados.
- **Botón "Nueva Búsqueda":** Navega a `/search?id=X` para iniciar el Wizard desde cero.
- **Botón "Abrir Carpeta":** Abre la carpeta local del proyecto en el explorador de archivos.
- **Notificaciones tipo toast:** Confirmación visual de acciones exitosas/erróneas.

**Pendiente:**
- **Botón "Iniciar Screening"** (habilitado solo si hay ≥1 búsqueda con artículos): navega a `/screening?id=X`.
- **Diagrama PRISMA en vivo** (futuro).

#### 3.2.1 Búsqueda Sistemática (`/search?id=X` → `search.astro` → `SearchWizard.tsx`)

**Estado actual (✅ Implementado):**

Wizard multi-paso modularizado en 4 sub-componentes React independientes:

| Paso | Componente | Descripción |
|------|-----------|-------------|
| 1. Describir | `SearchWizardDescribe.tsx` | El usuario escribe en lenguaje natural qué investiga. Selecciona área agrícola, rango de años e idioma. |
| 2. Revisar | `SearchWizardReview.tsx` | El LLM genera una query booleana optimizada, términos AGROVOC/MeSH sugeridos y desglose PICO/PEO. El usuario puede editar la query. |
| 3. Buscando | `SearchWizardSearching.tsx` | Ejecución concurrente. El backend usa primero otro llamado al LLM para **adaptar la sintaxis de la query** estrictamente según los requerimientos nativos de cada API elegida (OpenAlex, Semantic Scholar, ArXiv) mejorando drásticamente la relevancia de resultados sin fallar en sintaxis complejas. |
| 4. Resultados | `SearchWizardResults.tsx` | Tabla interactiva con todos los artículos encontrados. Soporte para **renderizado LaTeX** (KaTeX + `react-latex-next`) en títulos y abstracts. Columnas: título, autores (truncados a "et al." si son muy largos), año, journal, DOI (enlace), fuente (badge coloreado), estado de descarga, nombre de archivo PDF local. Botones de descarga masiva de PDFs (con nomenclatura automática `[año]_[primer_autor]_[título].pdf`) y **botón para subir PDF manualmente** si la descarga automática falla o está bloqueada por paywall. |

**Bases de datos soportadas:**
- 📚 OpenAlex (>200M works)
- 🔬 Semantic Scholar (AI-powered)
- 📄 ArXiv (preprints)
- 🌐 Web (BrowserMCP — backup)

#### 3.2.2 Screening / Cribado (`/screening?id=X` — ✅ Implementado)

Interfaz de cribado inspirada en **Rayyan.ai**, organizada en una única vista unificada (island renderizado con client:only="react") que intercala entre **2 sub-fases** lógicas, con traducción de abstracts vía LLM local.

**Reglas de negocio:**
- **Solo artículos con PDF descargado** (`download_status = SUCCESS`) entran al screening. Los artículos sin PDF (paywall, failed, pending) quedan excluidos.
- **Soporte Multi-Screening:** Se permite tener crear sesiones concurrentes por proyecto, ideal para que diversas personas trabajen simultáneamente (multi-persona).
- **Control de Artículos Libres (*Eligibility*):** Al crear una nueva revisión, el sistema contabiliza estrictamente si todos los artículos descargados ya están aglomerados por sesiones anteriores. En tal caso, bloquea la creación de revisiones vacías hasta recopilar más literatura.
- **Estrategia de Integridad de Base de Datos y UUIDs:** Todos los modelos (Proyectos, Búsquedas, Artículos, Revisiones y Decisiones) usan obligatoriamente un `UUIDv4` como Clave Primaria (tipo `String`). Esto asegura que es matemáticamente imposible que un ID de artículo de un proyecto se cruce con una revisión de otro proyecto, favoreciendo entornos asíncronos y manteniendo las relaciones Foreign Key inmutables.

##### Página 1: Configuración del Screening (`/screening?id=X` → `ScreeningSetup.tsx`)

**Si ya existe una sesión activa:**
- Muestra tarjeta con nombre, fecha, objetivo, estadísticas (total, revisados, incluidos, excluidos, tal vez), barra de progreso.
- Botón **"▶️ Continuar Screening"** → navega a la sesión activa.
- Botón **"🗑️ Eliminar sesión y crear nueva"** → elimina la sesión y todas sus decisiones (cadena de borrado en cascada del UUID), regresa al formulario de creación. Esta funcionalidad también se ha extendido al Dashboard, logrando una **eliminación segura de la revisión manteniendo ilesos los PDFs extraídos.**

**Si no hay sesión existente (formulario de creación de Nueva Revisión):**
- **Soporte Multi-Screening Inteligente:** Por omisión al dar clic, buscará artículos no asignados y sugerirá nombres de revisión en base al contador.
- **Nombre de la sesión y Objetivo:** Ambos son opcionales. El sistema asume nombres por default (Revisión N).
- **Selección de búsquedas (Filtro Condicional):** Checklist. Se ocultan por defecto todas las búsquedas que ya no contengan artículos disponibles (0 artículos no asignados). Las tarjetas visuales marcan la métrica y fuentes exactas por cada query del prompt.
- **Resumen consolidado:** Muestra el total de artículos no asignados únicos elegibles, con advertencia excluyente de lo que ya fue asignado previamente.
- **Idioma de lectura:** Selector (español/inglés/portugués).
- **Modelo de traducción:** Por defecto `aya:8b` (Cohere, multilingüe avanzado). Opciones: Llama 3.1 8B, Qwen 2.5 7B.
- **Enriquecimiento previo:** Al crear la sesión, se ejecuta automáticamente la extracción de abstracts y keywords desde los PDFs descargados (vía PyMuPDF).
- **Construcción Segura SQL:** Al hacer click en crear, un OUTER JOIN se encarga de acoplar matemática y exclusivamente a los artículos sin asignar con su nueva ronda invocando sus UUIDs, sin afectar el histórico PRISMA.

##### Página 2: Sesión de Screening (`/screening?id=X&session=Y` → `ScreeningSession.tsx`)

Interfaz principal de cribado artículo-por-artículo, estilo Rayyan:

**Área central — Tarjeta del artículo:**
- **Título** (con renderizado LaTeX si contiene fórmulas).
- **Autores** (truncados a 3 + "et al." si son más de 3), **Año**, **Journal**, **DOI** (enlace clicable al artículo original).
- **Abstract original** completo.
- **Abstract traducido** (si el idioma de lectura ≠ idioma original): traducción estrictamente literal ejecutada por el LLM local. **No se resume ni se parafrasea**: se traduce oración por oración manteniendo exactamente el contenido original.
- **Visor de PDF integrado:** Un botón permite desplegar un visor de PDF (iframe) directamente debajo del abstract para consultar el artículo original sin salir de la sesión.
- **Keywords** del artículo (si disponibles).
- **Fuente de la búsqueda** (badge: OpenAlex / Semantic Scholar / ArXiv).

**Botones de decisión:**
- ✅ **Incluir** (verde) — El artículo es relevante para la revisión.
- ❌ **Excluir** (rojo) — El artículo no cumple los criterios. Se solicita un **motivo de exclusión** (dropdown configurable: "Fuera de alcance", "No es artículo original", "Idioma no aceptado", "Duplicado no detectado", "Sin acceso al texto completo", "Otro").
- 🟡 **Tal Vez** (amarillo) — Dudoso, se revisará después.
- 📄 **Ver PDF** (gris) — Abre un iframe inferiør para visualizar el PDF cargado localmente.
- 📝 **Nota** (gris) — Campo de texto opcional para anotar observaciones.

**Atajos de teclado:**
- `I` → Incluir
- `E` → Excluir
- `M` → Tal Vez (Maybe)
- `←` / `→` → Artículo anterior / siguiente
- `N` → Abrir campo de nota
- `P` → Abrir / Cerrar visor de PDF

**Panel lateral — Estadísticas en vivo:**
- Barra de progreso: N revisados / N total.
- Contadores: N incluidos, N excluidos, N tal vez, N pendientes.
- Filtros rápidos: ver solo "Tal vez", ver solo pendientes, ir a un artículo específico por índice.

**Vista alternativa — Tabla completa:**
- Toggle para cambiar entre vista tarjeta (uno a uno) y vista tabla (todos los artículos con su estado de decisión).
- Permite revisión rápida del panorama general.

**Sub-componentes React:**

| Componente | Responsabilidad |
|-----------|----------------|
| `ScreeningSetup.tsx` | Gestión sesión existente (continuar/eliminar), formulario de nueva sesión (nombre, objetivo, búsquedas, idioma, modelo) |
| `ScreeningSession.tsx` | Orquestador de la sesión (carga artículos, gestión estado, teclado) |
| `ScreeningArticleCard.tsx` | Tarjeta individual del artículo con abstract + traducción |
| `ScreeningStats.tsx` | Panel lateral con progreso y contadores |
| `ScreeningListView.tsx` | Vista tabla alternativa con todos los artículos y estados |

#### 3.2.3 Chat RAG (`chat` — ⏳ Futuro, post-screening)
- **Chat conversacional** tipo NotebookLM con streaming de respuestas.
- Cada respuesta incluye **citaciones APA inline** (Autor et al., Año) y al final un bloque de "**Referencias**" con los DOI clicables.
- **Indicador de fuentes:** Cada fragmento de respuesta tiene un tooltip que señala de qué artículo y página se extrajo.
- **Modo Redacción:** Panel dividido donde a la izquierda está el chat y a la derecha un editor para el borrador del usuario (Introducción, Discusión, etc.). El LLM propone mejoras contextualizadas con la literatura indexada.
- **Exportar conversación:** Descarga en Markdown o PDF con las citas completas.

#### 3.2.4 Configuración del Proyecto (`settings` — ⏳ Futuro)
- Editar nombre, descripción, área agrícola. *(Parcialmente implementado en `ProjectDashboard.tsx`)*
- Configurar modelo LLM preferido (vía LiteLLM: Ollama local, OpenAI, Anthropic, etc.).
- Parámetros de RAG: tamaño de chunk, top-K de recuperación, umbral de similitud.
- Exportar/Importar proyecto completo (backup).

#### 3.2.5 Base de Datos (`data/agrisearch.db` — ✅ Implementado)
La arquitectura backend cuenta con su propia base de código documental que expone el comportamiento, ejemplos vivos y la estructura atómica de las tablas SQLite (`agrisearch.db`) mediante SQLAlchemy Async (`aiosqlite`).

*   **Identificadores Inmutables y Seguros (`UUIDv4`):** El mayor pilar del diseño de AgriSearch contra colisiones entre las revisiones concurrentes y los proyectos. Toda asignación genera dinámicamente UUIDs con cero colisiones probabilísticas.
*   **Recursos Aprobados:**
    *   `docs/database_schema_expected.json`: El diccionario exacto de qué información y restricciones de tabla requiere cada modelo SQLAlchemy en producción.
    *   `docs/database_schema_current.json`: Generado automáticamente mediante PRAGMAs para auditar el SQLite real.
    *   `docs/database_diagram.md`: Un diagrama ER completo construido en Mermaid ilustrando las relaciones Muchos-a-Muchos y Uno-a-Muchos que dominan la selección de artículos para screening y el almacenamiento histórico PRISMA.

### 3.3 Wireframe Conceptual del Flujo General

```mermaid
graph TD
    subgraph "Dashboard Principal /"
        A["📋 Lista de Proyectos"] --> B["➕ Crear Nuevo Proyecto"]
        A --> C["Click en tarjeta"]
    end

    subgraph "Consola de Proyecto /project?id=X"
        C --> D["📊 ProjectDashboard"]
        B --> D
        D --> E["📜 Historial de Búsquedas"]
        D --> F["🔍 Nueva Búsqueda"]
        D --> G["🗂️ Iniciar Screening"]
    end

    subgraph "Búsqueda Sistemática /search?id=X"
        F --> H1["Paso 1: Describir tema"]
        E -->|Click en búsqueda| H2["Paso 4: Ver resultados"]
        H1 --> H2b["Paso 2: Revisar query LLM"]
        H2b --> H3["Paso 3: Ejecutar búsqueda"]
        H3 --> H2["Paso 4: Resultados + Descarga PDFs"]
    end

    subgraph "Screening /screening?id=X"
        G -->|"≥1 búsqueda"| S1["Setup: Seleccionar búsquedas + idioma"]
        S1 --> S2["Sesión: Cribado artículo por artículo"]
        S2 --> S3{"Decisión"}
        S3 -->|"✅ Incluir"| S4["Pool de incluidos"]
        S3 -->|"❌ Excluir"| S5["Pool de excluidos + motivo"]
        S3 -->|"🟡 Tal vez"| S6["Revisión posterior"]
        S4 --> S7["Estadísticas PRISMA"]
    end

    subgraph "Futuro"
        S4 --> RAG["💬 Chat RAG + Redacción"]
        RAG --> EXP["📤 Exportar: CSV / PRISMA / Borrador"]
    end
```

**Leyenda de estados de implementación:**
- ✅ **Implementado:** Dashboard, Consola de Proyecto, Búsqueda Sistemática completa (4 pasos), Screening (Setup + Sesión interactivas con LLM).
- ⏳ **En proceso/diseño:** RAG vectorización de textos completos.
- 🔮 **Futuro:** Chat RAG, Redacción, Exportación PRISMA.

---

## 4. Plan de Acción: Fases y Sub-fases

---

### FASE 1: IDENTIFICACIÓN — Búsqueda Sistemática y Recopilación (🟢 COMPLETADO - PARCIAL)

> Corresponde a la etapa de **"Identification"** del diagrama de flujo PRISMA 2020. En esta fase ya tenemos conectividad con MCP (OpenAlex, Semantic Scholar, ArXiv), creación de proyectos e interfaz Astro/React conectada a FastAPI (SQLite).

---

#### Sub-fase 1.1: Definición de la Pregunta de Investigación y Construcción de Queries (✅ Completado)


**Propósito:**
Transformar la necesidad del investigador expresada en lenguaje natural en una estrategia de búsqueda bibliográfica formal, reproducible y con alta sensibilidad, adaptada al dominio agrícola.

**Argumentación Científica:**
PRISMA 2020 exige reportar de forma transparente la estrategia de búsqueda utilizada, incluyendo los términos, operadores booleanos y filtros aplicados en cada base de datos para garantizar la reproducibilidad (Page et al., 2021). En el dominio agrícola, la utilización de vocabularios controlados como AGROVOC de la FAO mejora sustancialmente el recall de las búsquedas (Aubin et al., 2006).

**Inputs:**
1. Descripción en lenguaje natural del tema de interés por parte del usuario.
2. Selección del área agrícola (entomología, fitopatología, breeding, etc.).
3. Criterios preliminares de inclusión/exclusión (rango de años, idiomas aceptados, tipos de publicación).
4. ID del proyecto activo en la plataforma.

**Acciones a Realizar:**
1. Capturar el input del usuario mediante el Wizard multi-paso en el frontend.
2. Enviar al backend vía `POST /api/v1/search/build-query`.
3. El `search_service.py` invoca a `llm_service.py` (vía LiteLLM → Ollama) con un prompt especializado que:
   - Identifica los conceptos PICO/PEO del input.
   - Genera sinónimos y variaciones terminológicas (EN/ES).
   - Propone términos AGROVOC relevantes.
   - Construye la query booleana final optimizada para cada base de datos.
4. Presentar la query propuesta al usuario para revisión y ajuste manual.
5. Almacenar la query aprobada en la base de datos del proyecto (`SearchQuery` model, tabla `search_queries`).
6. Permitir la iteración: el usuario puede refinar y re-ejecutar cuantas veces necesite.
7. Generar un log de auditoría de la query final (fecha, base, operadores) para el reporte PRISMA.
8. Validar que la query no esté vacía y que al menos una base de datos esté seleccionada.
9. Ofrecer templates de queries preconstruidas para áreas agrícolas comunes (ej. "control biológico en soja", "resistencia a fungicidas en trigo").
10. Guardar versiones históricas de las queries para trazabilidad.

**Outputs:**
- Query booleana/semántica aprobada y almacenada por base de datos.
- Log de auditoría de la estrategia de búsqueda.

**QA y Métricas:**
| Métrica | Umbral Aceptable |
|---------|-----------------|
| Query generada contiene al menos 3 conceptos PICO/PEO | 100% |
| Query validada sintácticamente para la API de destino | 100% |
| Tiempo de generación de query < 10 s | ≥ 95% de las veces |
| Log de auditoría generado correctamente | 100% |

**Flujograma:**
```mermaid
graph TD
    A[Usuario describe tema en lenguaje natural] --> B[Selecciona área agrícola y criterios]
    B --> C[Backend: LLM genera query booleana + sinónimos + AGROVOC]
    C --> D[Frontend: Presenta query al usuario]
    D --> E{¿Aprueba?}
    E -->|Sí| F[Almacenar query aprobada en BD del proyecto]
    E -->|No| G[Usuario edita manualmente]
    G --> D
    F --> H[Generar log de auditoría]
```

---

#### Sub-fase 1.2: Ejecución de la Búsqueda Masiva en Bases de Datos (✅ Completado — Refactorizado)

**Propósito:**
Ejecutar las queries aprobadas contra múltiples bases de datos científicas y consolidar los resultados en un dataset único, desduplicado y trazable por proyecto.

**Argumentación Científica:**
PRISMA 2020 requiere reportar el número de registros identificados en cada base de datos y el número de duplicados removidos (Page et al., 2021). La combinación de múltiples fuentes reduce el sesgo de publicación y aumenta la exhaustividad de la revisión (Cochrane Handbook, Higgins et al., 2019).

**Inputs:**
1. Conceptos y sinónimos extraídos por el LLM en la Sub-fase 1.1 (JSON estructurado).
2. Bases de datos seleccionadas (OpenAlex, Semantic Scholar, ArXiv).
3. Parámetros de paginación y límites máximos.

**Acciones a Realizar:**
1. **Construcción determinista de queries** (`query_builder.py`): para cada base de datos, el código (NO un LLM) genera la query óptima según la sintaxis de cada API:
   - **OpenAlex**: texto plano con keywords separados por espacio (`search=keyword1 keyword2 synonym1`).
   - **Semantic Scholar**: keywords concisas sin operadores booleanos complejos.
   - **ArXiv**: formato `all:"concept1" AND (all:"concept1" OR all:"synonym1")`.
2. Invocar en paralelo (asyncio) los clientes: `openalex_client.py`, `semantic_scholar_client.py`, `arxiv_client.py`.
3. Implementar paginación automática para cada API hasta el límite configurado.
4. Normalizar los resultados al schema interno `Article` (DOI, título, autores, año, abstract, fuente, URL).
5. Ejecutar deduplicación multi-nivel: primero por DOI exacto, luego por similitud de título (fuzzy matching con Levenshtein ≥ 0.85).
6. Registrar la procedencia de cada artículo (de qué base provino, incluyendo duplicados detectados).
7. Almacenar todos los artículos en la tabla `articles` asociados al `project_id`.
8. Generar el conteo por base de datos para el diagrama PRISMA (N identificados por base, N duplicados).
9. Retornar `adapted_queries` en la respuesta API para que el usuario vea exactamente qué query se envió a cada base de datos.
10. Validar que los DOIs retornados sean válidos (formato correcto con regex `10.\d{4,}/.*`).

**Outputs:**
- Dataset consolidado y desduplicado almacenado en BD.
- `adapted_queries`: queries exactas enviadas a cada API (para transparencia y reproducibilidad).
- Reporte de conteos por base (Para diagrama PRISMA: N de cada fuente, N duplicados).

**QA y Métricas:**
| Métrica | Umbral Aceptable |
|---------|-----------------|
| Duplicados removidos correctamente (precision) | ≥ 98% |
| Artículos únicos verificados contra DOI | 100% |
| Tasa de error de conexión a APIs < 2% | ≥ 98% disponibilidad |
| Query builder genera queries válidas por API | 100% (18 tests unitarios) |

**Flujograma:**
```mermaid
graph TD
    A["Conceptos + sinónimos (Sub-fase 1.1)"] --> B["query_builder.py: genera query por API"]
    B --> C["build_openalex_query()"]
    B --> D["build_semantic_scholar_query()"]
    B --> E["build_arxiv_query()"]
    C --> F{"Consultar en paralelo asyncio"}
    D --> F
    E --> F
    F -->|OpenAlex| G["Resultados OpenAlex"]
    F -->|Semantic Scholar| H["Resultados Semantic Scholar"]
    F -->|ArXiv| I["Resultados ArXiv"]
    G --> J["Normalización al schema Article"]
    H --> J
    I --> J
    J --> K["Deduplicación por DOI + fuzzy title"]
    K --> L["Almacenar en BD con project_id"]
    L --> M["Retornar resultados + adapted_queries"]
```

---

#### Sub-fase 1.3: Descarga de Textos Completos (Full-Text Retrieval) (✅ Completado)

**Propósito:**
Obtener los PDFs de texto completo de los artículos identificados como open access, validar los DOIs de los que no se obtuvieron, y habilitar la subida manual por parte del usuario.

**Argumentación Científica:**
La evaluación del riesgo de sesgo y la extracción de datos a profundidad requieren ineludiblemente el artículo a texto completo y no solo metacatos o abstracts (Higgins et al., 2019, Cochrane Handbook cap. 4).

**Inputs:**
1. Lista de artículos de la Sub-fase 1.2 con DOI o URL de open access.
2. Configuración de rate-limiting y timeouts.

**Acciones a Realizar:**
1. Para cada artículo, verificar si el DOI resuelve a un PDF open access usando la API de Unpaywall (`api.unpaywall.org`).
2. Implementar descarga asíncrona con `aiohttp` y gestión de rate-limit (máx. 10 req/seg por defecto).
3. Validar que el archivo descargado sea un PDF válido (magic bytes `%PDF`).
4. Nombrar los archivos siguiendo un esquema reproducible: `{doi_sanitizado}_{primer_autor}_{año}.pdf`.
5. Almacenar en `data/projects/{project_uuid}/pdfs/`.
6. Actualizar la tabla `articles` con el campo `download_status` ∈ {`success`, `failed`, `paywall`, `not_found`}.
7. Generar un reporte de artículos no descargados para que el usuario los busque manualmente.
8. Proveer endpoint `POST /api/v1/documents/upload` para que el usuario suba PDFs manualmente.
9. Al recibir un PDF manual, validar que el DOI coincida con un artículo existente en el proyecto.
10. Actualizar automáticamente el diagrama PRISMA: N artículos con texto completo vs no.
11. Ofrecer un botón de "Reintentar fallidos" para volver a intentar las descargas que fallaron por timeout.
12. Generar estadísticas de descarga: % open access obtenidos, % paywall, % errores.

**Outputs:**
- Carpeta `data/projects/{id}/pdfs/` poblada con los textos completos.
- CSV/BD actualizada con columna `download_status` y `local_path`.
- Reporte de artículos pendientes para búsqueda manual del usuario.

**QA y Métricas:**
| Métrica | Umbral Aceptable |
|---------|-----------------|
| Tasa de éxito de descargas OA | ≥ 80% |
| PDFs validados como archivos reales | 100% |
| Timeout handling sin crashes | 100% |
| Correspondencia DOI ↔ PDF almacenado | 100% |

---

#### Sub-fase 1.4: Refactorización y Mejoras de Interfaz (Separación de Dashboard de Proyectos y Buscador) (✅ Completado)

**Propósito:**
Mejorar la experiencia de usuario (UX) separando lógicamente la gestión de proyectos y el historial de búsquedas de la propia interfaz de creación de nuevas búsquedas, permitiendo una navegación directa y modularizada.

**Argumentación Científica:**
La claridad en las herramientas de software para investigación bibliométrica incide directamente en la reducción de errores humanos operativos durante la configuración de tareas. Múltiples flujos cognitivos dentro de un único componente de UI generan saturación y potenciales conflictos en la recuperación de búsquedas anteriores (Nielsen, 1994).

**Inputs:**
1. Componente monolítico `SearchWizard` con lógicas mezcladas de visualización de historial y formulario de nueva consulta.

**Acciones a Realizar:**
1. Desvincular la lógica de gestión de "Proyectos" creando un `ProjectDashboard.tsx` independiente.
2. Migrar la tabla de historial de búsqueda hacia la vista del proyecto para un acceso directo (`/project?id=X`).
3. Refactorizar el ruteo hacia `SearchWizard.tsx` para aceptar `query_id` a través de URL y omitir los pasos de generación si existe (`/search?id=X&query_id=Y`).
4. Mejorar la interfaz general del `Dashboard.tsx` manejando posibles desbordamientos de texto en descripciones incompletas.
5. Optimizar la transferencia de datos entre frontend y backend limitando respuestas genéricas de listas de artículos a un máximo seguro (e.g. 200 items por página) previniendo errores de colapso de parseo JSON.
6. Aplicar ajustes de despliegue mediante una actualización del `.gitignore`.

**Outputs:**
- Nueva página y componente de detalles del proyecto.
- `SearchWizard` estrictamente encargado del Wizard y de la visualización pura.

**QA y Métricas:**
| Métrica | Umbral Aceptable |
|---------|-----------------|
| Rutas accesibles de forma programática (Shareable URLs) | 100% |
| Eliminación del estado de paso `"dashboard"` en el Wizard | 100% |

---

#### Sub-fase 1.5: Integración de Nuevos MCPs para Búsqueda (Bases de Datos Científicas Avanzadas) (En Progreso)

**Propósito:**
Ampliar significativamente el alcance y la exhaustividad de la búsqueda sistemática incorporando servidores MCP especializados que permiten el acceso a bases de datos de alto impacto (Web of Science, Scopus, Google Scholar, PubMed, etc.), estandarizando a su vez su modelo de datos estructurado.

**Argumentación Científica:**
Para adherirse plenamente a la declaración PRISMA 2020 y minimizar el sesgo de publicación, es crucial consultar múltiples y diversas bases de datos biomédicas, de agricultura y multidisciplinares. Herramientas emergentes basadas en protocolos como MCP facilitan una conexión flexible y enriquecen los metadatos de los papers, reduciendo el ruido en el screening.

**Servidores a Integrar:**
1. **`paper-search-mcp-nodejs`:** Es el más completo. Soporta Web of Science, Google Scholar, PubMed, y más. Unifica el modelo de datos para asegurar que todos los resúmenes y metadatos se vean iguales en la vista de resultados.
2. **`Scientific-Papers-MCP`:** Especializado en metadatos enriquecidos de OpenAlex y Crossref.
3. **`scholar_mcp_server`:** Excelente si se necesita acceso a Scopus y ScienceDirect (requiere API Key institucional del usuario final).

**Acciones a Realizar:**
1. **Verificación de Entorno:** Evaluar las dependencias técnicas de cada MCP (Node.js, Python, keys) e inicializar un archivo de configuración (ej. `mcp_config.json`) o variables de entorno para su orquestación.
2. **Implementación de Clientes Internos:** En `backend/app/services/mcp_clients/`, implementar un cliente unificado o múltiples adaptadores que envuelvan las llamadas a estos nuevos servidores MCP (especialmente enfocado a `paper-search-mcp-nodejs`).
3. **Mapeo de Datos:** Implementar normalizadores para transformar las salidas de formato unificado al modelo de dominio `Article` (`Article(doi=..., title=...)`).
4. **UI del Wizard:** Integrar checkboxes para "PubMed", "Google Scholar", "WOS" y "Scopus" en `SearchWizard.tsx` (`DB_OPTIONS`).
5. **Manejo de Errores Específicos:** Abordar timeouts de scrapping o denegaciones de API Keys con mensajes claros para el usuario final mostrados como feedback en la fase de "Ejecutando Búsqueda".

**Outputs:**
- Integración end-to-end de los 3 nuevos servidores MCP listados en la interfaz para que el usuario pueda consultarlos de forma paralela u opcional.
- Documento guía auxiliar para explicar al científico cómo obtener una API Key Institucional en el caso de usar Elsevier/Scopus.

**QA y Métricas:**
| Métrica | Umbral Aceptable |
|---------|-----------------|
| Normalización de DOIs y Autores es coherente y unificada | 100% |
| Manejo grácil (Graceful fallback) ante error de llaves API expiradas | 100% |
| Performance paralela al consultar PubMed junto a ArXiv | ≤ 20 seg por página|

---

### FASE 2: CRIBADO Y ELEGIBILIDAD — Screening PRISMA

> Corresponde a las etapas de **"Screening"** y **"Eligibility"** del diagrama de flujo PRISMA 2020. Esta fase es la más crítica del flujo PRISMA ya que determina qué artículos formarán la base del conocimiento del investigador. Incluye el **pre-procesamiento estructurado** de PDFs, la **generación de resúmenes**, el **screening interactivo con Active Learning**, la **indexación RAG** de los artículos definitivos, y la **asistencia predictiva** basada en las decisiones del usuario.

---

#### Sub-fase 2.0: Pre-procesamiento Estructurado de PDFs (PDF → Markdown Enriquecido)

**Propósito:**
Convertir cada PDF descargado en un documento Markdown estructurado de alta fidelidad que preserve la jerarquía del paper (secciones, subsecciones), las tablas, las fórmulas matemáticas y las figuras, generando un formato óptimo para chunking semántico y para el screening visual. Esta sub-fase es el **fundamento de calidad** de todo el pipeline RAG posterior.

**Argumentación Científica:**
**Docling** (Auer et al., 2024; Livathinos et al., 2025) es un toolkit open-source de IBM que utiliza modelos especializados de IA para el análisis de layout (**DocLayNet**) y el reconocimiento de estructura de tablas (**TableFormer**). A diferencia de extractores planos como `PyPDFLoader`, Docling preserva la estructura semántica del documento y convierte fórmulas matemáticas a LaTeX. Ouyang et al. (2024) demostraron con **OmniDocBench** que los métodos de parsing basados en modelos de layout superan significativamente a los extractores baseline en documentos con tablas complejas y contenido multi-columna. El pre-procesamiento PDF→MD está validado en el repositorio TFM-allucination del mismo autor, donde este pipeline redujo la tasa de alucinación del RAG en un ~15% al preservar la integridad semántica del corpus.

> **Nota de experiencia previa:** Este enfoque fue implementado exitosamente en el proyecto TFM del autor (`TFM-allucination/scripts/preprocess_corpus.py` y `src/knowledge/parsers.py`), donde demostró que la conversión estructurada con Docling + TableFlattener + VLM produce chunks de calidad significativamente superior a la extracción plana.

**Inputs:**
1. PDFs descargados en la Fase 1 (campo `local_pdf_path` de la tabla `articles`).
2. Metadatos de cada artículo (DOI, autores, año, título, journal, keywords).

**Acciones a Realizar:**

1. **Extracción Estructurada con Docling (`DoclingParser`):**
   - Configurar `PdfPipelineOptions` con:
     - `do_table_structure = True` (modo `ACCURATE` de TableFormer).
     - `do_formula_enrichment = True` (fórmulas → LaTeX).
     - `do_ocr = True` con `EasyOcrOptions(lang=["en", "es", "pt"])` para documentos escaneados.
     - `generate_picture_images = True` para extraer figuras.
   - Invocar `DocumentConverter().convert(pdf_path)` → obtener `DoclingDocument`.
   - Exportar a Markdown: `result.document.export_to_markdown()`.
   - El Markdown preserva: `## Secciones`, tablas nativas `| col | ...`, fórmulas `$...$`, y referencias a imágenes.

2. **Inferencia Visual de Figuras (`ImageFilter` + VLM Local):**
   - Para cada imagen extraída por Docling, enviarla a un VLM local (`llama3.2-vision` vía Ollama) configurado de forma **determinista** (temperature=0.0, penalización de repetición).
   - **Guardrail de imágenes:** Si la imagen es un logo, barra decorativa, marca de agua o header institucional → responder `DESCARTAR` y omitirla.
   - Si la imagen contiene datos técnicos (gráfico, diagrama, mapa, foto de campo) → generar descripción textual de 2-3 oraciones.
   - Inyectar la descripción en el Markdown con semántica: `> **[💡 Descripción de Imagen VLM]:** "Gráfico de barras mostrando la relación entre concentración de azoxystrobin y tasa de mortalidad del patógeno..."`.

3. **Aplanamiento Analítico de Tablas (`TableFlattener`):**
   - Los LLMs y los generadores de embeddings pierden contexto al hacer chunking sobre tablas Markdown.
   - El `TableFlattener` detecta bloques de tabla con regex y convierte cada fila en una oración descriptiva que **siempre referencia sus cabeceras**:
   ```
   Entrada (tabla):
   | Cultivo | Tratamiento | Rendimiento (t/ha) |
   |---------|-------------|-------------------|
   | Trigo   | Fungicida A | 4.2               |

   Salida (oración):
   "Según Wang et al. (2023), Cultivo: Trigo, Tratamiento: Fungicida A,
    Rendimiento: 4.2 t/ha."
   ```
   - Esto produce **Dense High-Quality Retrieval**: cada "aplanado" es una unidad atómica de información perfecta para embeddings.

4. **Inyección de Metadatos como Front-matter YAML:**
   - Prepend a cada `.md` un bloque YAML con metadatos del artículo:
   ```yaml
   ---
   agrisearch_id: "a1b2c3d4-e5f6-7890"
   doi: "10.1016/j.compag.2023.107500"
   title: "YOLO-based crop phenology detection"
   authors: "Wang J., Zhang H., Li M."
   year: 2023
   journal: "Computers and Electronics in Agriculture"
   keywords: ["YOLO", "phenology", "precision agriculture"]
   source_database: "openalex"
   ---
   ```
   - Esto permite que el pipeline de chunking posterior inyecte automáticamente los metadatos de procedencia en cada chunk.

5. **Almacenamiento del corpus procesado:**
   - Guardar cada `.md` final en `data/projects/{project_uuid}/parsed/{doi_sanitized}.md`.
   - Actualizar la tabla `articles` con el campo `local_md_path` apuntando al Markdown procesado.
   - Registrar estadísticas: N tablas aplanadas, N imágenes procesadas, N fórmulas LaTeX detectadas.

6. **Procesamiento en batch asíncrono:**
   - Ejecutar con `asyncio.Semaphore(3)` para no saturar los modelos locales (Docling + VLM usan GPU/CPU intensivamente).
   - Progress bar en frontend con `SSE` (Server-Sent Events) mostrando: "Procesando artículo 3 de 15... (20%)".
   - Timeout de 120 segundos por PDF; skip con log de error si falla.

**Stack Tecnológico:**
| Tecnología | Versión | Propósito |
|-----------|---------|-----------|
| **Docling** | ≥ 2.x | Parser PDF→MD con DocLayNet + TableFormer (MIT license) |
| **docling-core** | ≥ 2.x | Tipos de datos: `DoclingDocument`, `PictureItem`, `TableItem` |
| `llama3.2-vision` (vía Ollama) | 11B | VLM local para descripción de figuras (determinista, CPU/GPU) |
| `EasyOCR` | ≥ 1.7 | Motor OCR para documentos escaneados (integrado en Docling) |
| `SQLAlchemy` | ≥ 2.x | Actualización del campo `local_md_path` en `articles` |

**Outputs:**
- Directorio `data/projects/{project_uuid}/parsed/` con un `.md` por artículo PDF.
- Tabla `articles` actualizada con `local_md_path`.
- Estadísticas de procesamiento (tablas, imágenes, fórmulas).

**QA y Métricas:**
| Métrica | Umbral Aceptable |
|---------|-----------------|
| PDFs convertidos exitosamente a Markdown | ≥ 95% |
| Tablas detectadas y aplanadas correctamente | ≥ 90% |
| Fórmulas LaTeX preservadas | ≥ 85% |
| Imágenes con descripción VLM útil (no decorativas) | ≥ 80% |
| Front-matter YAML con DOI y metadatos completos | 100% |
| Tiempo promedio de procesamiento por PDF | < 60 s |

**Tests:** `tests/unit/test_pdf_preprocessing.py`
- Conversión PDF→MD genera archivo no vacío
- Front-matter YAML contiene DOI y año
- TableFlattener convierte tabla a oración con cabeceras
- ImageFilter descarta logos (mock del VLM con respuesta `DESCARTAR`)
- Fórmulas LaTeX preservadas en el Markdown

**Flujograma:**
```mermaid
graph TD
    classDef step fill:#2d3748,stroke:#4a5568,stroke-width:1.5px,color:#e2e8f0
    classDef parser fill:#2c7a7b,stroke:#4fd1c5,stroke-width:1.5px,color:#fff
    classDef db fill:#2b6cb0,stroke:#63b3ed,stroke-width:1.5px,color:#fff

    subgraph "📄 Sub-fase 2.0: PDF → Markdown Enriquecido"
        PDF(["📄 PDFs descargados"]):::step --> Docling["DoclingParser + TableFormer + LaTeX"]:::parser
        Docling -->|Detecta figuras| VLM["Ollama: llama3.2-vision"]:::db
        VLM -->|"Guardrail: DESCARTAR / Descripción"| Docling
        Docling --> MD["Markdown Crudo + Descripciones VLM"]:::step
        MD --> Flatten["TableFlattener: tabla → oración"]:::parser
        META(["📋 Metadatos del artículo (BD)"]):::step --> YAML["Inyección Front-matter YAML"]:::step
        Flatten --> YAML
        YAML --> Parsed["📂 data/projects/{uuid}/parsed/*.md"]:::step
        Parsed --> DB["Actualizar articles.local_md_path"]:::db
    end
```

---

#### Sub-fase 2.1: Generación de Resúmenes Estructurados para Screening

**Propósito:**
Pre-procesar los artículos generando resúmenes estructurados mediante LLM que faciliten la toma de decisión rápida por parte del investigador, reduciendo la carga cognitiva del cribado. Estos resúmenes se generan a partir del **Markdown enriquecido** de la Sub-fase 2.0 (no solo del abstract), lo que permite capturar metodología, resultados y conclusiones que el abstract podría omitir.

**Argumentación Científica:**
El uso de herramientas de aprendizaje automático para el screening de títulos y abstracts ha demostrado reducir la carga de trabajo de los investigadores en más del 50%, manteniendo alta sensibilidad en las inclusiones (Ouzzani et al., 2016). La plataforma ASReview demostró que los enfoques de Active Learning pueden reducir hasta en un 95% el esfuerzo de screening sin pérdida significativa de recall (van de Schoot et al., 2021). Vares (2026) introdujo **AutoDiscover**, un framework que modela la literatura como un grafo heterogéneo y usa Thompson Sampling adaptativo para el screening, demostrando mejoras significativas sobre baselines estáticos en el benchmark **SYNERGY de 26 datasets**.

**Inputs:**
1. Artículos con Markdown procesado (Sub-fase 2.0) **o** solo abstract (para artículos sin PDF).
2. Criterios de inclusión/exclusión definidos por el usuario en la Sub-fase 1.1.
3. Objetivo y alcance del proyecto (campo `description` de `projects`).

**Acciones a Realizar:**
1. Para cada artículo, construir un prompt que reciba el **abstract + primera sección del MD** (si existe) para contexto enriquecido:
   - Genere un resumen estructurado de 3-5 oraciones enfocado al tema del proyecto.
   - Identifique la metodología principal (ensayo de campo, in vitro, modelado, meta-análisis, revisión).
   - Extraiga las variables de interés agrícola (cultivo, plaga, tratamiento, rendimiento, región geográfica).
   - Evalúe preliminarmente la relevancia según los criterios de inclusión/exclusión del proyecto.
   - Genere un JSON estructurado: `{"summary": "...", "methodology": "...", "variables": {...}, "relevance_label": "posiblemente_relevante", "relevance_score": 0.85, "key_findings": "..."}`.
2. Almacenar los resúmenes en la tabla `articles` (campos: `llm_summary`, `relevance_score`, `methodology_type`, `agri_variables_json`).
3. Generar una etiqueta de relevancia (`posiblemente_relevante`, `posiblemente_irrelevante`, `incierto`) con score de confianza [0.0, 1.0].
4. Calcular keywords agrícolas predominantes con **TF-IDF** sobre los abstracts del proyecto.
5. Crear clusters temáticos mediante embeddings (`nomic-embed-text`) para agrupar artículos similares visualmente → input directo para el **Grafo Temático** de la Fase 4.
6. Procesar en batch con control de concurrencia (`asyncio.Semaphore(5)` para no saturar Ollama).
7. Manejar artículos sin abstract ni PDF: generar resumen del título + metadatos disponibles, marcando `confidence: low`.
8. Guardar el prompt utilizado para auditoría y reproducibilidad (campo `generation_prompt_hash`).
9. Calcular el tiempo promedio por resumen para estimar el tiempo total al usuario.
10. Verificar que cada resumen generado no exceda de 200 palabras.
11. **Nuevo:** Para artículos con PDF procesado, el resumen puede basarse en el MD completo (Introducción + Conclusiones) → resúmenes más informativos que los basados solo en abstract.

**Outputs:**
- Todos los artículos enriquecidos con `llm_summary`, `relevance_score`, `methodology_type`, y `agri_variables_json`.
- Clusters temáticos para visualización en el frontend y como semilla para el Grafo Temático (Fase 4).

**QA y Métricas:**
| Métrica | Umbral Aceptable |
|---------|-----------------|
| Resúmenes generados para todos los artículos con abstract o MD | 100% |
| Score de relevancia asignado a cada artículo | 100% |
| Tiempo promedio por resumen (abstract only) | < 5 s |
| Tiempo promedio por resumen (abstract + MD sections) | < 15 s |
| Coherencia del resumen vs abstract original (evaluación manual de muestra) | ≥ 90% |
| Variables agrícolas extraídas correctamente (muestra de 20 artículos) | ≥ 85% |

**Tests:** `tests/unit/test_summary_generation.py`
- Resumen JSON tiene campos obligatorios
- Score de relevancia está en rango [0.0, 1.0]
- Resumen no excede 200 palabras
- Variables agrícolas se extraen como JSON válido
- Artículos sin abstract generan resumen desde título

**Flujograma:**
```mermaid
graph TD
    A["Artículos con MD procesado (2.0) o solo abstract"] --> B["Batch de N artículos"]
    B --> C{"¿Tiene Markdown procesado?"}
    C -->|Sí| D["LLM: abstract + Introducción + Conclusiones del MD"]
    C -->|No| E["LLM: solo abstract + título + keywords"]
    D --> F["Generar resumen JSON estructurado"]
    E --> F
    F --> G["Extraer variables agrícolas"]
    G --> H["Asignar relevance_score + label"]
    H --> I["Calcular keywords TF-IDF"]
    I --> J["Clustering por embeddings"]
    J --> K["Almacenar en BD enriched"]
    K --> L{"¿Más artículos?"}
    L -->|Sí| B
    L -->|No| M["Artículos listos para screening manual"]
```

---

#### Sub-fase 2.2: Screening Interactivo Asistido por Active Learning (Estilo Rayyan)

**Propósito:**
Presentar al investigador una interfaz visual de clasificación artículo-por-artículo donde pueda etiquetar la relevancia, con traducción de abstracts vía LLM local y atajos de teclado para maximizar la velocidad del cribado. El sistema aprende iterativamente de las decisiones del usuario para re-priorizar los artículos pendientes (**Active Learning**), mostrando primero los de mayor incertidumbre.

**Argumentación Científica:**
Rayyan utiliza un clasificador SVM (Support Vector Machine) que aprende de las decisiones del usuario para predecir la clasificación de registros no revisados, mostrando un ahorro de tiempo del 40% en promedio (Ouzzani et al., 2016). ASReview extiende esta idea con Active Learning: tras cada decisión del usuario, el modelo recalcula las prioridades y presenta primero los artículos con mayor incertidumbre, maximizando la eficiencia del esfuerzo humano (van de Schoot et al., 2021). Miwa et al. (2014) demostraron que el screening basado en certeza puede reducir la carga de trabajo en un 30-70% sin pérdida significativa de recall. Vares (2026) demostró con **AutoDiscover** que modelar la literatura como un **grafo heterogéneo** con Thompson Sampling adaptativo mitiga significativamente el problema de **cold-start** (cuando hay pocas decisiones iniciales), superando a los baselines estáticos en el benchmark SYNERGY.

**Inputs:**
1. Artículos enriquecidos de la Sub-fase 2.1 (con resúmenes LLM, scores y clusters).
2. Decisiones previas del usuario (si las hay).
3. Selección de búsquedas a incluir en el screening (configurado en la página de Setup).
4. Idioma de lectura preferido para la traducción de abstracts.

**Arquitectura de Interfaz (2 páginas):**

**Página 1 — Configuración del Screening (`/screening?id=X` → `ScreeningSetup.tsx`):**
1. Mostrar todas las `SearchQuery` del proyecto como una checklist seleccionable.
2. El usuario elige qué búsquedas incluir en la sesión de cribado (o selecciona todas).
3. Mostrar el total consolidado de artículos únicos (ya desduplicados entre las búsquedas seleccionadas).
4. Selector de idioma de lectura: español, inglés, portugués.
5. Recomendación automática de modelo de traducción Ollama: por defecto `llama3.1:8b`, con sugerencias alternativas como `aya-23` o `madlad400` para traducción EN↔ES/PT más precisa.
6. Selector de **estrategia de priorización inicial**: por `relevance_score` (default), por año descendente, por cluster temático, o aleatorio.
7. Botón "Iniciar Screening" que crea la sesión y navega a la interfaz de cribado.

**Página 2 — Sesión de Screening (`/screening?id=X&session=Y` → `ScreeningSession.tsx`):**

**Acciones a Realizar:**
1. Presentar artículos en la interfaz de screening, priorizados por `relevance_score` descendente inicialmente.
2. Mostrar por cada artículo: título (con LaTeX renderizado), autores, año, journal, DOI (enlace clicable), abstract completo, keywords, fuente (badge de color: OpenAlex/Semantic Scholar/arXiv), y la **sugerencia del LLM** con barra de confianza visual (★★★★☆).
3. **Nuevo: Vista previa del Markdown procesado:** Si el artículo tiene `local_md_path`, mostrar un toggle "📄 Ver texto completo procesado" que expande las secciones del MD (Introducción, Metodología, Resultados, Conclusiones) en acordeones colapsables. Esto permite screening por texto completo cuando el abstract es insuficiente.
4. **Traducción de abstracts:** Si el idioma de lectura configurado difiere del idioma original del abstract, invocar el LLM local para generar una traducción **estrictamente literal** (oración por oración, sin resumir ni parafrasear). Cachear la traducción en BD para no re-computar.
5. El usuario clasifica con **3 estados**: **✅ Incluir** (verde), **❌ Excluir** (rojo — con motivo obligatorio), o **🟡 Tal Vez** (amarillo — revisión posterior).
6. **Motivos de exclusión** (dropdown configurable): "Fuera de alcance", "No es artículo original (revisión/editorial)", "Idioma no aceptado", "Duplicado no detectado", "Sin acceso al texto completo", "Metodología inadecuada", "Otro" (campo libre).
7. **Nota del revisor:** Campo de texto opcional para anotar observaciones.
8. **Atajos de teclado:** `I` = Incluir, `E` = Excluir, `M` = Tal Vez (Maybe), `←`/`→` = Artículo anterior/siguiente, `N` = Abrir campo de nota, `T` = Toggle texto completo.
9. Tras cada bloque de N decisiones (configurable, por defecto 10), ejecutar el **re-entrenamiento del modelo de priorización**:
   - Tomar los embeddings de artículos decididos (ya calculados en Sub-fase 2.1).
   - Entrenar un clasificador ligero (`LogisticRegression` de scikit-learn o `SGDClassifier` para eficiencia) con las etiquetas del usuario.
   - Re-ordenar los artículos pendientes por: `P(incluir|embeddings) × incertidumbre`.
   - **Estrategia de Active Learning:** Presentar primero los artículos con mayor incertidumbre (`uncertainty sampling: |P(include) - 0.5| < ε`), lo que maximiza la información ganada por cada decisión humana.
10. Actualizar los puntajes de sugerencia del LLM en la interfaz en tiempo real.
11. Registrar cada decisión con timestamp, motivo de exclusión, nota del revisor, y versión del modelo.
12. Permitir filtros: ver solo "Tal Vez", ver solo pendientes, ver solo de mayor confianza LLM, filtrar por cluster temático.
13. **Panel lateral con estadísticas en tiempo real:** N revisados / N total (barra visual animada), N incluidos, N excluidos, N tal vez, N pendientes, gráfico de evolución temporal.
14. **Vista alternativa tabla:** Toggle entre vista tarjeta (uno a uno) y vista tabla completa de todos los artículos con su estado.
15. Permitir cambiar decisiones pasadas (audit trail con historial de cambios).
16. Generar el motivo de exclusión agregado para el diagrama PRISMA.
17. Al completar el screening (100% revisados o el usuario indica suficiente), consolidar la lista final de incluidos.
18. Exportar el log de decisiones como CSV para transparencia.
19. **Nuevo:** Alerta de potencial sesgo de exclusión: si el modelo detecta que el usuario está excluyendo artículos que el clasificador predice como relevantes, mostrar un warning sutil sugiriendo reconsideración.

**Sub-componentes Frontend:**

| Componente | Responsabilidad |
|-----------|----------------|
| `ScreeningSetup.tsx` | Selección de búsquedas, configuración idioma/modelo/estrategia, inicio sesión |
| `ScreeningSession.tsx` | Orquestador de sesión (carga artículos, gestión estado, event listeners teclado) |
| `ScreeningArticleCard.tsx` | Tarjeta individual: metadata + abstract original + abstract traducido + toggle MD |
| `ScreeningMarkdownPreview.tsx` | **Nuevo:** Acordeones con secciones del MD procesado (Intro, Método, Resultados) |
| `ScreeningStats.tsx` | Panel lateral: barra de progreso, contadores, filtros rápidos, gráfico temporal |
| `ScreeningListView.tsx` | Vista tabla alternativa con todos los artículos y estados de decisión |

**Outputs:**
- Artículos clasificados en: Incluidos vs Excluidos (con motivo) vs Tal Vez.
- Abstracts traducidos cacheados en BD.
- Log de decisiones exportable con justificaciones y timestamps.
- Modelo entrenado de priorización persistido (serializado a `joblib` por sesión).
- Estadísticas de screening para el diagrama PRISMA.

**QA y Métricas:**
| Métrica | Umbral Aceptable |
|---------|-----------------|
| Recall del modelo de priorización (artículos relevantes en top 50%) | ≥ 90% |
| F1-score del clasificador vs decisiones humanas (tras ≥30 decisiones) | ≥ 0.80 |
| Latencia de la interfaz al pasar de artículo en artículo | < 500 ms |
| Calidad de traducción (evaluación manual de muestra de 20 abstracts) | ≥ 90% fidelidad |
| Completitud del log de auditoría | 100% |
| Reducción de tiempo de screening vs screening manual puro | ≥ 40% |
| Tiempo de re-entrenamiento Active Learning (tras N=10 decisiones) | < 2 s |

**Tests:** `tests/unit/test_screening_session.py`
- Clasificador entrenado con ≥10 samples predice correctamente (F1 > 0.6)
- Uncertainty sampling selecciona artículos con P(include) ≈ 0.5
- Log de auditoría registra timestamp + decisión + motivo
- Atajos de teclado mapean correctamente a decisiones
- Cambio de decisión mantiene historial previo

**Flujograma:**
```mermaid
graph TD
    A0["Página 1: ScreeningSetup"] --> A0a["Seleccionar búsquedas"]
    A0a --> A0b["Configurar idioma + estrategia de priorización"]
    A0b --> A0c["Iniciar sesión de screening"]
    A0c --> A["Artículos enriquecidos priorizados"]
    A --> T{"¿Idioma ≠ original?"}
    T -->|Sí| T1["LLM traduce abstract literal"]
    T -->|No| B
    T1 --> B["Presentar artículo en Frontend"]
    B --> MD{"¿Tiene Markdown procesado?"}
    MD -->|Sí| MD1["Mostrar toggle '📄 Ver texto completo'"]
    MD -->|No| C
    MD1 --> C
    C --> D{"Decisión del usuario o atajo de teclado"}
    D -->|"✅ Incluir (I)"| E["Pool de incluidos"]
    D -->|"❌ Excluir (E)"| F["Registrar motivo de exclusión"]
    D -->|"🟡 Tal Vez (M)"| G["Revisión posterior"]
    E & F & G --> H{"¿N=10 decisiones alcanzadas?"}
    H -->|Sí| I["Re-entrenar clasificador (Active Learning)"]
    I --> J["Re-priorizar pendientes (uncertainty sampling)"]
    J --> B
    H -->|No| B
    I --> K["Actualizar estadísticas PRISMA en vivo"]
    I --> BIAS{"¿Alerta de sesgo potencial?"}
    BIAS -->|Sí| WARN["⚠️ Mostrar warning de reconsideración"]
```

---

#### Sub-fase 2.3: Indexación RAG de Artículos Incluidos (Chunking Semántico sobre Markdown)

**Propósito:**
Fragmentar, vectorizar e indexar los **Markdown enriquecidos** (generados en Sub-fase 2.0) de los artículos incluidos para habilitar la recuperación semántica precisa necesaria para el chat RAG y la asistencia de redacción, combatiendo directamente la alucinación de los LLMs.

**Argumentación Científica:**
La Generación Aumentada por Recuperación (RAG) previene la "confabulación" heurística de los LLMs anclando sus respuestas exclusivamente al corpus provisto (Lewis et al., 2020). Gao et al. (2024) realizaron un survey comprensivo de las técnicas RAG, destacando que **la calidad del chunking y la preservación de metadatos son factores críticos** para la precisión del retrieval. Paper-qa (Future-House) demostró que la inclusión de metadatos de procedencia (DOI, autores, página) en cada chunk mejora sustancialmente la trazabilidad de las citas generadas.

**Avances clave del chunking semántico reciente:**
- Jimeno Yepes et al. (2024) demostraron que el **chunking basado en tipo de elemento estructural** (sección, tabla, figura) supera al chunking de tamaño fijo tradicional, ya que preserva la unidades semánticas completas del documento.
- Mortezaagha & Rahgozar (2026) introdujeron **GraLC-RAG**, un framework que combina late chunking con estructura de grafo, demostrando que el chunking structure-aware logra 15.6× más diversidad de secciones recuperadas que los métodos basados solo en similitud de contenido.
- Taiwo & Yusoff (2026) evaluaron empíricamente 4 estrategias de chunking y concluyeron que el **structure-aware chunking** ofrece el mejor rendimiento general en retrieval con significativamente menores costos computacionales.

**Diferencia crítica vs. plan anterior:** En lugar de parsear los PDFs directamente con `pymupdf4llm` durante el chunking, esta sub-fase **opera sobre los Markdown ya procesados por Docling en la Sub-fase 2.0**, aprovechando la estructura semántica preservada (secciones, tablas aplanadas, fórmulas LaTeX, descripciones de imágenes).

**Inputs:**
1. Archivos Markdown procesados de artículos marcados como "Incluidos" (`data/projects/{uuid}/parsed/*.md`).
2. Metadatos completos de cada artículo (DOI, autores, año, título) — ya disponibles en el front-matter YAML del MD.

**Acciones a Realizar:**
1. **Leer cada `.md` procesado** y parsear el front-matter YAML para obtener metadatos automáticamente.
2. **Chunking semántico por estructura del Markdown:**
   - Detectar secciones por headers (`##`, `###`) del Markdown.
   - Cada sección es una unidad de chunking natural; si excede 800 tokens, subdividir por párrafos con overlap de 100 tokens.
   - **Las tablas aplanadas** (generadas por TableFlattener) son chunks individuales completos — nunca se cortan a mitad.
   - **Las descripciones VLM** de imágenes se adjuntan al chunk de la sección donde aparecen.
   - Las fórmulas LaTeX se mantienen intactas dentro de su chunk.
   - Chunks de 300-800 tokens (rango dinámico según tipo de contenido).
3. **Enriquecer cada chunk con metadatos de procedencia:**
   ```json
   {
     "chunk_id": "chunk_001",
     "doi": "10.1016/j.compag.2023.107500",
     "authors": "Wang J., Zhang H.",
     "year": 2023,
     "title": "YOLO-based crop phenology detection",
     "section": "3. Results",
     "element_type": "paragraph|table_flat|image_description|formula",
     "page_range": "5-6",
     "project_id": "proj-uuid-001"
   }
   ```
4. Generar embeddings locales con `nomic-embed-text` vía Ollama (768 dimensiones).
5. Almacenar en **Qdrant** en una **colección aislada por proyecto**: `project_{uuid}`.
6. Crear un índice invertido complementario para búsquedas exactas (**BM25** con `rank_bm25`).
7. Implementar un **híbrido retriever (vector + BM25)** con re-ranking por score fusionado (Reciprocal Rank Fusion).
8. Verificar la integridad: para cada artículo, contar N chunks generados y validar que todos estén en Qdrant.
9. Generar un mapeo `chunk_id → {doi, page, section, element_type}` para la **trazabilidad de citas** (citación automática en el chat RAG).
10. Manejar artículos sin PDF/MD: indexar solo el abstract + metadatos como un chunk único.
11. Ejecutar un **test de sanidad**: query de prueba con un término clave del artículo → debe retornar ≥1 chunk de ese artículo en top-5.
12. Logging de todo el proceso de indexación (N artículos, N chunks, N chunks por tipo, errores).
13. Permitir re-indexación si el usuario agrega/quita artículos del pool incluido.

**Stack Tecnológico:**
| Tecnología | Propósito |
|-----------|-----------| 
| `nomic-embed-text` (vía Ollama) | Embeddings de 768 dimensiones |
| `Qdrant` (local, persistido) | Vector database con colecciones aisladas por proyecto |
| `rank_bm25` | Índice BM25 complementario para retrieval léxico |
| `scikit-learn` | Re-ranking (Reciprocal Rank Fusion) |
| `PyYAML` | Parsing del front-matter YAML de cada MD |

**Outputs:**
- Colección Qdrant `project_{uuid}` poblada y consultable.
- Índice BM25 complementario.
- Mapeo de trazabilidad `chunk_id → source_metadata` (JSON).

**QA y Métricas:**
| Métrica | Umbral Aceptable |
|---------|-----------------|
| Recall@10 en queries de prueba por artículo | ≥ 0.85 |
| Cada chunk tiene DOI y section trazable | 100% |
| Dimensión de embeddings consistente (768) | 100% |
| Tablas aplanadas indexadas como chunks atómicos (no cortadas) | 100% |
| Tiempo de indexación por artículo (promedio, desde MD) | < 15 s |
| Test de sanidad exitoso (artículo en top-5) | 100% |

**Tests:** `tests/unit/test_rag_indexing.py`
- Chunking por secciones Markdown genera chunks con headers
- Tablas aplanadas son chunks atómicos (no subdivididos)
- Front-matter YAML se inyecta en metadatos de cada chunk
- Chunks no exceden 800 tokens
- Test de sanidad: query → chunk del artículo correcto

**Flujograma:**
```mermaid
graph TD
    A["📂 Markdown procesados (Sub-fase 2.0)"] --> B["Leer MD + parsear front-matter YAML"]
    B --> C["Detectar secciones por headers ##/###"]
    C --> D{"¿Sección > 800 tokens?"}
    D -->|Sí| E["Subdividir por párrafos con overlap 100"]
    D -->|No| F["Chunk = sección completa"]
    E --> G["Inyectar metadatos (DOI, section, element_type)"]
    F --> G
    G --> H["Generar embeddings con nomic-embed-text"]
    H --> I["Almacenar en Qdrant: project_{uuid}"]
    I --> J["Crear índice BM25 complementario"]
    J --> K["Configurar Hybrid Retriever (RRF)"]
    K --> L["Verificación de integridad"]
    L --> M["Test de sanidad con query de prueba"]
    M --> N["Pipeline RAG listo para Chat (Fase 3)"]
```

---

#### Sub-fase 2.4: Asistencia Inteligente Predictiva (AI Suggestions) durante el Screening

**Propósito:**
Ayudar al investigador a mantener la consistencia en los criterios de inclusión y exclusión durante sesiones muy largas de screening. Mediante el análisis del historial de decisiones, el sistema genera predicciones **Few-Shot** basadas en el patrón de inclusión/exclusión del usuario, reduciendo la fatiga cognitiva y actuando como un "segundo revisor automatizado" que no reemplaza la decisión humana pero la informa.

**Argumentación Científica:**
Reducir la fatiga cognitiva es crítico en la fase de screening: O'Mara-Eves et al. (2015) demostraron que la consistencia inter-revisor disminuye significativamente después de las primeras ~50 decisiones. Usar un motor de sugerencias tipo "Active Learning / Few-Shot" que presenta evidencia contextual reduce la discrepancia en lecturas repetitivas. Vares (2026) formalizó este concepto con AutoDiscover, usando un agente adaptativo que gestiona un portfolio de estrategias de query dinámicamente, incluyendo un dashboard visual para interpretar y diagnosticar las decisiones del agente (TS-Insight).

**Inputs:**
1. Historial de decisiones del usuario en la sesión actual (≥10 decisiones).
2. Abstracts y embeddings de los artículos decididos.
3. Abstract del artículo actual a evaluar.
4. Criterios de inclusión/exclusión del proyecto.

**Acciones a Realizar:**
1. **Activación:** El asistente se activa automáticamente a partir del artículo 11 (tras 10 decisiones manuales, suficientes para un Few-Shot de calidad).
2. **Compilación del contexto Few-Shot:**
   - Recuperar las últimas 10 decisiones más recientes (5 incluidos + 5 excluidos, balanceados) con su abstract.
   - Incluir los motivos de exclusión como contexto adicional.
   - Construir un prompt Few-Shot:
     ```
     Eres un asistente de cribado PRISMA. Basándote en las decisiones previas
     del investigador, predice si el siguiente artículo debería ser incluido
     o excluido.

     --- Decisiones previas (ejemplos) ---
     [Incluido]: "YOLO-based crop phenology..." → Incluido
     [Excluido]: "Survey of blockchain in supply chain..." → Excluido (Fuera de alcance)
     ...

     --- Artículo a evaluar ---
     Título: "..."
     Abstract: "..."

     Responde en JSON: {"suggested_status": "include|exclude|uncertain",
                         "justification": "...",
                         "confidence": 0.0-1.0,
                         "key_match_reasons": ["..."]}
     ```
3. El backend endpoint `GET /api/v1/sessions/{session_id}/articles/{article_id}/suggestion` compila y ejecuta la query.
4. El LLM (Ej. `llama3.1:8b` o `aya:8b`) emite el JSON de sugerencia.
5. **Frontend renderiza:**
   - Banner visual sobre el abstract: "🤖 Sugerencia: **Incluir** (87% confianza)" con color verde/rojo/amarillo.
   - Tooltip con la justificación del motivo.
   - Indicador de los `key_match_reasons` resaltados en el abstract (highlighting de frases clave).
6. **Refinamiento continuo:** Cada nueva decisión del usuario actualiza el pool de ejemplos Few-Shot.
7. **Métricas de precisión del asistente:** Comparar suggestion vs decisión final del usuario para Track el accuracy acumulado del asistente (visible en el panel de estadísticas).
8. **Opción de desactivar:** Toggle en la UI para que el usuario pueda ocultar las sugerencias si lo desea.

**Stack Tecnológico:**
| Tecnología | Propósito |
|-----------|-----------| 
| LLM local (vía LiteLLM → Ollama) | Generación de sugerencias Few-Shot |
| FastAPI endpoint | `GET /sessions/{id}/articles/{id}/suggestion` |
| `Pydantic` v2 | Validación del JSON de respuesta |
| `scikit-learn` | Clasificador complementario (usado en Sub-fase 2.2) |

**Outputs:**
- Sugerencias JSON por artículo con status, justificación y confianza.
- Métricas de accuracy del asistente (suggestion vs decisión real).
- Log de sugerencias para análisis post-hoc.

**QA y Métricas:**
| Métrica | Umbral Aceptable |
|---------|-----------------|
| Accuracy de la sugerencia vs decisión final del usuario | ≥ 75% (tras ≥30 decisiones) |
| Latencia de generación de la sugerencia | < 3 s |
| Formato JSON de sugerencia válido | 100% |
| Sugerencia activada solo tras ≥10 decisiones | 100% |
| Confianza de la sugerencia correlaciona con accuracy real | ≥ 0.60 (Spearman) |

**Tests:** `tests/unit/test_ai_suggestions.py`
- Sugerencia no se activa con < 10 decisiones
- JSON de respuesta tiene campos obligatorios
- Confianza está en rango [0.0, 1.0]
- Balance del contexto Few-Shot (≈50% include / ≈50% exclude)
- Accuracy tracking se actualiza correctamente

**Flujograma:**
```mermaid
graph TD
    A{"¿reviewed_count ≥ 10?"} -->|No| B["Sin sugerencia: screening manual puro"]
    A -->|Sí| C["Recuperar últimas 10 decisiones (balanceadas)"]
    C --> D["Construir prompt Few-Shot con contexto"]
    D --> E["LLM genera sugerencia JSON"]
    E --> F{"¿JSON válido?"}
    F -->|Sí| G["Frontend: banner visual con sugerencia"]
    F -->|No| H["Fallback: sin sugerencia para este artículo"]
    G --> I["Usuario decide (posiblemente influenciado)"]
    I --> J["Comparar sugerencia vs decisión real"]
    J --> K["Actualizar accuracy tracking del asistente"]
    K --> L["Añadir decisión al pool Few-Shot"]
    L --> A
```

---


### FASE 3: INCLUSIÓN Y SÍNTESIS — Asistente de Redacción

> Corresponde a la etapa de **"Included"** del diagrama PRISMA 2020, donde se trabaja con los artículos finales seleccionados.

---

#### Sub-fase 3.1: Chat RAG Conversacional con Citación APA Estricta

**Propósito:**
Proveer una interfaz de chateo conversacional tipo "NotebookLM" donde el LLM responda basándose exclusivamente en los artículos incluidos del proyecto, citando rigurosamente en formato APA 7ª edición y señalando las fuentes primarias consultadas.

**Argumentación Científica:**
Emplear LLMs como herramientas conversacionales colaborativas mejora la organización discursiva y la síntesis de literatura (Hosseini et al., 2023), siempre que exista transparencia demostrada mediante citación íntegra y estandarizada. Paper-qa (Future-House/paper-qa) demostró que un pipeline RAG con prompts estrictos de citación puede lograr precisión estado del arte en QA sobre documentos científicos, reduciendo las alucinaciones a niveles mínimos. La clave es el anclaje del LLM al contexto recuperado y la instrucción explícita de nunca fabricar citas.

**Inputs:**
1. Pregunta/mensaje del usuario en el chat (EN o ES).
2. Colección Qdrant del proyecto (indexada en Sub-fase 2.3).
3. Historial de la conversación para mantener contexto.

**Acciones a Realizar:**
1. Recibir el mensaje del usuario en `POST /api/v1/chat/message`.
2. Ejecutar hybrid retrieval (Qdrant vector search + BM25) con top-K configurable (default K=15).
3. Re-rankear los chunks recuperados con un cross-encoder ligero o con el propio LLM.
4. Construir el prompt de sistema que instruya rigurosamente:
   - "Responde ÚNICAMENTE basándote en los fragmentos proporcionados."
   - "Cita SIEMPRE usando formato APA 7ª edición inline: (Autor et al., Año)."
   - "Al final incluye un bloque '## Referencias' con las citas completas y DOI."
   - "Si no encuentras información suficiente en los fragmentos, indica explícitamente que no tienes datos para responder."
   - "NUNCA inventes citas o referencias."
5. Inyectar los chunks recuperados con sus metadatos en el contexto del prompt.
6. Invocar el LLM vía LiteLLM con streaming habilitado.
7. Parsear la respuesta para extraer las citas inline y validarlas contra la base:
   - Para cada cita `(Autor, Año)`, verificar que existe un artículo en la BD del proyecto con ese autor y año.
   - Marcar citas no verificadas con un indicador de advertencia.
8. Enviar la respuesta mediante SSE (Server-Sent Events) al frontend para renderizado progresivo.
9. Almacenar el mensaje y la respuesta en el `chat_history` del proyecto.
10. En el frontend, cada cita inline es un enlace clicable que muestra un tooltip con el título completo, DOI, y los chunks utilizados.
11. Proveer botón de "Verificar citas" que ejecuta una validación post-hoc de todas las referencias.
12. Soportar follow-up questions usando el conversation_id para mantener contexto.
13. Permitir exportar toda la conversación como Markdown con las referencias al final.

**Outputs:**
- Respuesta en texto natural debidamente sustentada y citada en APA.
- Bloque de Referencias con DOIs.
- Indicadores de confiabilidad (citas verificadas vs no verificadas).

**QA y Métricas:**
| Métrica | Umbral Aceptable |
|---------|-----------------|
| Hallucination Check: citas APA inexistentes en 20 corridas de prueba | 0% de citas inventadas |
| Citas en formato APA 7ª ed. correcto | ≥ 95% |
| Respuestas que incluyen al menos 1 cita | ≥ 90% |
| Latencia de primera respuesta (streaming) | < 3 s |
| Chunks recuperados relevantes (evaluación manual) | ≥ 80% |

**Flujograma:**
```mermaid
sequenceDiagram
    participant U as Usuario
    participant FE as Frontend
    participant API as FastAPI
    participant Q as Qdrant
    participant BM as BM25 Index
    participant LLM as LiteLLM/Ollama

    U->>FE: Escribe pregunta en chat
    FE->>API: POST /api/v1/chat/message
    API->>Q: Búsqueda vectorial top-K
    API->>BM: Búsqueda BM25 top-K
    Q-->>API: Chunks vectoriales con metadatos
    BM-->>API: Chunks BM25 con metadatos
    API->>API: Fusión + Re-ranking de chunks
    API->>LLM: Prompt estricto APA + Contexto chunks
    LLM-->>API: Streaming de respuesta citada
    API->>API: Validar citas contra BD del proyecto
    API-->>FE: SSE streaming con citas verificadas
    FE-->>U: Respuesta renderizada con Referencias
```

---

#### Sub-fase 3.2: Asistencia Integral de Redacción Académica

**Propósito:**
Ir más allá del chat para asistir directamente al investigador en la redacción de sus trabajos académicos (TFM, tesis, paper), detectando lagunas de literatura, sugiriendo mejoras de estilo científico y verificando la correcta citación contra la base documental indexada.

**Argumentación Científica:**
Los modelos de lenguaje actuales operan no solo como motores de recuperación sino como evaluadores de coherencia argumental y correctores idiomáticos de estilo científico (Hosseini et al., 2023). La integración de RAG con asistencia de redacción permite identificar afirmaciones no respaldadas y sugerir citas pertinentes del corpus del investigador, reduciendo el riesgo de plagio accidental y fortaleciendo la argumentación.

**Inputs:**
1. Texto borrador del investigador (pegado en el editor o subido como .docx/.txt).
2. Sección específica que está redactando (Introducción, Marco Teórico, Metodología, Discusión, etc.).
3. Colección Qdrant del proyecto.

**Acciones a Realizar:**
1. Recibir el borrador en `POST /api/v1/writing/analyze`.
2. Segmentar el texto en oraciones/párrafos.
3. Para cada afirmación factual detectada:
   - Buscar en el índice RAG si existe respaldo en los artículos incluidos.
   - Si hay respaldo: sugerir la cita APA correspondiente.
   - Si no hay respaldo: marcar como "Afirmación sin respaldo" con sugerencia de búsqueda.
4. Evaluar la calidad de redacción científica:
   - Detectar lenguaje informal o no técnico.
   - Sugerir vocabulario más preciso para el dominio agrícola.
   - Identificar párrafos demasiado largos o sin estructura clara.
5. Verificar las citas existentes en el borrador:
   - ¿Están en formato APA correcto?
   - ¿Corresponden a artículos en la base del proyecto?
   - ¿El contenido citado se alinea con lo que dice el artículo original?
6. Generar un "Feedback Report" estructurado con secciones:
   - Afirmaciones sin respaldo.
   - Citas sugeridas.
   - Mejoras de estilo.
   - Errores de formato APA.
7. Soportar análisis en español e inglés.
8. Guardar el historial de revisiones para trazar el progreso del borrador.
9. Permitir la iteración: el usuario corrige, re-envía, y recibe un nuevo análisis.
10. Opción de exportar el feedback como un documento Markdown o PDF.

**Outputs:**
- Feedback Report con afirmaciones sin respaldo, citas sugeridas, mejoras de estilo y errores APA.
- Borrador anotado con sugerencias inline.

**QA y Métricas:**
| Métrica | Umbral Aceptable |
|---------|-----------------|
| Afirmaciones sin respaldo detectadas (precision) | ≥ 85% |
| Citas sugeridas relevantes al contexto | ≥ 80% |
| Detección de errores APA | ≥ 95% |
| Tiempo de análisis de un borrador de 2000 palabras | < 30 s |

---

### FASE 4: EXPLORACIÓN BIBLIOGRÁFICA — Grafos de Citación y Relación Temática (Estilo ResearchRabbit)

> Esta fase añade una capa de **exploración y descubrimiento visual** que permite al investigador navegar las conexiones entre los artículos incluidos y el universo de literatura relacionada, siguiendo el paradigma de herramientas como **ResearchRabbit** (nodos verdes = artículos en colección, azules = citados pero no descargados). Se construyen **dos bases de datos de grafos** complementarias por proyecto: una basada en **citas bibliográficas** y otra en **relación temática semántica**.

---

#### Sub-fase 4.1: Extracción de Referencias Bibliográficas de Artículos Incluidos

**Propósito:**
Recopilar la lista completa de referencias bibliográficas de cada artículo incluido en el screening, normalizando los DOIs y metadatos para alimentar el grafo de citaciones.

**Argumentación Científica:**
El análisis de redes de citación es fundamental para comprender la estructura intelectual de un campo de investigación y descubrir artículos seminales que podrían haberse omitido en la búsqueda inicial (Brack et al., 2021). Las herramientas como ResearchRabbit operan precisamente sobre esta lógica: a partir de un conjunto semilla de artículos ("seed papers"), se expande la red citacional para descubrir trabajos relacionados no evidentes mediante búsqueda por keywords (Jia & Saule, 2018).

**Inputs:**
1. Lista de artículos marcados como "Incluidos" en la Fase 2 (screening).
2. DOIs y external_ids de cada artículo.
3. PDFs descargados (para extracción con GROBID como fallback).

**Acciones a Realizar:**
1. Para cada artículo incluido, consultar las APIs existentes para obtener sus referencias:
   - **OpenAlex API:** Campo `referenced_works` — retorna una lista de IDs de todos los artículos citados. Resolución vía `GET /works/{id}` para obtener DOI + metadatos de cada referencia.
   - **Semantic Scholar API:** Campo `references` — retorna paperId, DOI, título, autores y año de cada referencia.
2. Normalizar los DOIs extraídos (remover prefijos `https://doi.org/`, `http://dx.doi.org/`, etc.).
3. Para artículos sin datos en APIs externas, utilizar **GROBID** (parser de PDFs) como fallback para extraer la sección de bibliografía del PDF y parsear las entradas.
4. Crear registros en la nueva tabla `article_references` de SQLite con:
   - `source_article_id` (FK al artículo que cita)
   - `cited_doi`, `cited_title`, `cited_authors`, `cited_year`
   - `extraction_source` (openalex | semantic_scholar | grobid | manual)
   - `is_in_project` (booleano: True si el DOI citado ya existe entre los artículos del proyecto)
5. Deduplicar las referencias entre múltiples fuentes (mismo DOI extraído de OpenAlex y Semantic Scholar).
6. Calcular estadísticas: total de referencias únicas, % de cobertura por fuente, artículos más citados entre los incluidos.
7. Marcar con `is_in_project = True` las referencias cuyo DOI coincida con algún artículo ya presente en el proyecto.
8. Ejecutar en batch asíncrono con rate-limiting para no saturar las APIs.

**Stack Tecnológico:**
| Tecnología | Propósito |
|-----------|-----------|
| `aiohttp` | Consultas asíncronas a OpenAlex y Semantic Scholar |
| `pymupdf4llm` | Parsing de bibliografía de PDFs (fallback) |
| GROBID (Docker, opcional) | Parser especializado de referencias en PDFs |
| `SQLAlchemy` | ORM para la nueva tabla `article_references` |

**Outputs:**
- Tabla `article_references` poblada con todas las citas de cada artículo incluido.
- Estadísticas de cobertura de extracción.

**QA y Métricas:**
| Métrica | Umbral Aceptable |
|---------|-----------------|
| Artículos incluidos con referencias extraídas | ≥ 90% |
| DOIs normalizados correctamente (formato `10.XXXX/...`) | 100% |
| Deduplicación de referencias entre fuentes | 100% |
| Tiempo de extracción por artículo | < 5 s |

**Tests:** `tests/unit/test_reference_extraction.py` (13 tests)
- Parsing de `referenced_works` de OpenAlex
- Parsing de `references` de Semantic Scholar
- Normalización de DOIs (variantes URL, prefijo DOI:, etc.)
- Modelo `article_references` con campos requeridos
- Flag `is_in_project`

**Flujograma:**
```mermaid
graph TD
    A["Artículos incluidos (screening)"] --> B{"¿Tiene DOI?"}
    B -->|Sí| C["Consultar OpenAlex: referenced_works"]
    B -->|Sí| D["Consultar Semantic Scholar: references"]
    B -->|No / Fallo| E["GROBID: parsear PDF bibliografía"]
    C --> F["Normalizar DOIs"]
    D --> F
    E --> F
    F --> G["Deduplicar entre fuentes"]
    G --> H["Marcar is_in_project"]
    H --> I["Almacenar en article_references"]
    I --> J["Estadísticas de cobertura"]
```

---

#### Sub-fase 4.2: Construcción del Grafo de Citaciones

**Propósito:**
Construir un grafo dirigido donde cada nodo es un artículo y cada arista representa una relación de cita bibliográfica. Los artículos incluidos se visualizan en **verde** y los citados pero no descargados en **azul**, permitiendo al investigador identificar inmediatamente qué literatura adicional podría ser relevante para descargar.

**Argumentación Científica:**
Los grafos de citación permiten identificar artículos seminales (altamente citados), clusters temáticos y potenciales lagunas en la cobertura de la revisión. Jia & Saule (2018) demostraron que la distribución de grados de los artículos citados en el subgrafo de proyección sigue una ley de potencia, lo que permite identificar tanto los trabajos canónicos (hub) como artículos relevantes poco conectados ("non-obvious papers") que los métodos convencionales no encuentran. La combinación de múltiples tipos de información (autor, venue, keywords) mejora significativamente la recomendación de citas (Brack et al., 2021).

**Inputs:**
1. Tabla `article_references` poblada en la Sub-fase 4.1.
2. Tabla `articles` del proyecto (para obtener metadatos de los incluidos).

**Acciones a Realizar:**
1. **Crear nodos de artículos incluidos** (status: `included`, color: `#22c55e` verde):
   - Propiedades: `doi`, `title`, `authors`, `year`, `journal`, `agrisearch_article_id`.
2. **Crear nodos de artículos citados externos** (status: `cited_external`, color: `#3b82f6` azul):
   - Propiedades: `doi`, `title`, `authors`, `year` (extraídos de `article_references`).
   - Estos nodos representan artículos que aparecen en las bibliografías pero **no están descargados** en el proyecto.
3. **Crear aristas dirigidas** `CITES`: desde el artículo que cita hacia el artículo citado.
   - Propiedades: `extraction_source` (de dónde se obtuvo la relación).
4. Calcular métricas del grafo:
   - **In-degree** de cada nodo: artículos más citados.
   - **Artículos puente**: nodos externos (azules) citados por ≥2 artículos incluidos (candidatos prioritarios para descargar).
   - **Citas compartidas**: pares de artículos incluidos que citan los mismos artículos externos (indicador de similitud bibliométrica).
5. Almacenar el grafo usando **NetworkX** (en memoria, serializado a JSON por proyecto) o **Neo4j** (si se prefiere una base de datos dedicada).
6. Proveer endpoint API: `GET /api/v1/graphs/{project_id}/citation` que retorne el grafo en formato compatible con **vis-network** (nodos + aristas con colores).
7. Soportar filtros: rango de años, status (solo incluidos, solo externos), profundidad de expansión.

**Stack Tecnológico:**
| Tecnología | Propósito |
|-----------|-----------|
| `NetworkX` ≥ 3.x | Biblioteca Python para grafos en memoria (dirigidos/no-dirigidos) |
| **Neo4j Community** (Docker, opcional) | Base de datos de grafos con Cypher para queries complejas |
| `neo4j-python-driver` ≥ 5.x | Conector Python → Neo4j (si se usa Neo4j) |
| `vis-network` (vis.js) | Visualización frontend interactiva de grafos force-directed |

**Outputs:**
- Grafo de citaciones almacenado (JSON o Neo4j) por proyecto.
- API endpoint que retorna nodos y aristas con colores para frontend.
- Métricas de centralidad: artículos más citados, artículos puente.

**QA y Métricas:**
| Métrica | Umbral Aceptable |
|---------|-----------------|
| Nodos del grafo == artículos incluidos + citas externas únicas | 100% |
| Aristas dirigidas correctamente (A→B = A cita a B) | 100% |
| Colores verde (incluido) y azul (externo) asignados correctamente | 100% |
| Tiempo de construcción del grafo para 100 artículos | < 10 s |

**Tests:** `tests/unit/test_citation_graph.py` (11 tests)
- Construcción del grafo dirigido con NetworkX
- Colores verde para incluidos, azul para externos
- Dirección de aristas (A cita B ≠ B cita A)
- Nodo más citado (in-degree)
- Serialización a JSON compatible con vis-network

**Flujograma:**
```mermaid
graph TD
    A["article_references"] --> B["Crear nodos INCLUDED (verde)"]
    A --> C["Crear nodos CITED_EXTERNAL (azul)"]
    B --> D["Crear aristas CITES dirigidas"]
    C --> D
    D --> E["Calcular in-degree por nodo"]
    E --> F["Identificar artículos puente"]
    F --> G["Serializar a JSON"]
    G --> H["API: GET /graphs/{id}/citation"]
    H --> I["Frontend: vis-network renderiza"]
```

---

#### Sub-fase 4.3: Construcción del Grafo de Relación Temática (Similitud Semántica)

**Propósito:**
Construir un segundo grafo **no-dirigido** basado en la **similitud semántica** entre artículos incluidos, usando embeddings de sus abstracts y títulos. A diferencia del grafo de citaciones (que refleja relaciones explícitas entre bibliografías), este grafo modela relaciones **implícitas**: artículos que tratan temas similares, usan metodologías comparables o estudian los mismos cultivos/plagas, incluso si no se citan mutuamente.

**Argumentación Científica:**
La combinación de grafos de citación con grafos de similitud semántica proporciona una visión holística del campo de investigación, capturando tanto las relaciones explícitas (citas) como las implícitas (proximidad temática). Brack et al. (2021) demostraron que la combinación de information retrieval textual con knowledge graphs científicos mejora significativamente la recomendación de citas (+0.8% MAP@50). Maharjan (2024) propuso un benchmark estandarizado para evaluar modelos de recomendación de citas, enfatizando la necesidad de considerar múltiples features del contexto citacional.

**Inputs:**
1. Artículos incluidos con abstract y título.
2. Embeddings generados por `nomic-embed-text` (768 dimensiones, ya disponibles en Qdrant de la Sub-fase 2.3).

**Acciones a Realizar:**
1. Para cada artículo incluido, obtener o generar su vector de embedding del abstract + título.
2. Calcular la **matriz de similitud coseno** entre todos los pares de artículos incluidos.
3. Aplicar un **umbral configurable** (default: 0.75) para crear aristas solo entre artículos suficientemente similares.
4. Para cada arista, enriquecer con:
   - `cosine_similarity`: score de similitud [0.0, 1.0].
   - `shared_keywords`: keywords que comparten ambos artículos (intersección de sus listas de keywords/topics).
   - `relationship_type`: categoría de la relación inferida por LLM (`same_methodology`, `same_crop`, `same_technology`, `complementary`, `general`).
5. Extraer 5 keywords/topics por artículo mediante LLM (si no se extrajeron previamente) para enriquecer las etiquetas de los nodos.
6. Detectar **clusters temáticos** automáticamente (artículos fuertemente conectados entre sí) usando algoritmos de community detection (Louvain o Girvan-Newman).
7. Almacenar el grafo usando NetworkX (serializado a JSON) o Neo4j.
8. Proveer endpoint API: `GET /api/v1/graphs/{project_id}/thematic` con el mismo formato vis-network.
9. El **grosor de las aristas** es proporcional al score de similitud.
10. Soportar que el usuario ajuste el umbral en la UI mediante un slider.

**Stack Tecnológico:**
| Tecnología | Propósito |
|-----------|-----------|
| `nomic-embed-text` (vía Ollama) | Embeddings de 768 dimensiones (ya en el stack) |
| `scikit-learn` | `cosine_similarity` para la matriz de distancias |
| `NetworkX` ≥ 3.x | Grafo no-dirigido + algoritmos de community detection |
| LLM local (vía LiteLLM) | Extracción de keywords y clasificación de tipo de relación |
| `vis-network` (vis.js) | Visualización frontend con aristas de grosor variable |

**Outputs:**
- Grafo temático no-dirigido almacenado por proyecto.
- Clusters temáticos auto-detectados.
- API endpoint con nodos y aristas (similitud como atributo).

**QA y Métricas:**
| Métrica | Umbral Aceptable |
|---------|-----------------|
| Artículos del mismo dominio agrícola con similarity > 0.7 | ≥ 80% |
| Artículos de dominios distintos con similarity < 0.5 | ≥ 70% |
| Clusters temáticos coherentes (evaluación manual de muestra) | ≥ 85% |
| Tiempo de cálculo de la matriz de similitud para 100 artículos | < 5 s |

**Tests:** `tests/unit/test_thematic_graph.py` (15 tests)
- Similitud coseno (vectores idénticos, ortogonales, nulos)
- Umbral de filtrado (default 0.75, estricto 0.95, relajado 0.0)
- Extracción de keywords compartidas
- Construcción del grafo no-dirigido
- Aristas con score y keywords

**Flujograma:**
```mermaid
graph TD
    A["Artículos incluidos"] --> B["Obtener embeddings (nomic-embed-text)"]
    B --> C["Calcular matriz cosine_similarity"]
    C --> D{"¿similarity >= umbral?"}
    D -->|Sí| E["Crear arista RELATED_BY_TOPIC"]
    D -->|No| F["Descartar par"]
    E --> G["Enriquecer: shared_keywords"]
    G --> H["LLM: classificar relationship_type"]
    H --> I["Detectar clusters (Louvain)"]
    I --> J["Serializar a JSON"]
    J --> K["API: GET /graphs/{id}/thematic"]
    K --> L["Frontend: vis-network con grosor variable"]
```

---

#### Sub-fase 4.4: API REST para Consulta y Exploración de Grafos

**Propósito:**
Exponer endpoints REST que permitan al frontend solicitar los datos de los grafos en formato JSON compatible con vis-network, con filtros de búsqueda, expansión de vecindad y estadísticas.

**Inputs:**
1. Grafos de citación y temático construidos en las Sub-fases 4.2 y 4.3.
2. Parámetros de consulta del frontend (project_id, filtros, profundidad).

**Acciones a Realizar:**
1. Implementar los siguientes endpoints en `backend/app/api/v1/graphs.py`:

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/v1/graphs/{project_id}/citation` | Grafo de citaciones completo (nodos + aristas) |
| `GET` | `/api/v1/graphs/{project_id}/thematic` | Grafo temático completo |
| `GET` | `/api/v1/graphs/{project_id}/article/{doi}/neighbors` | Vecinos de un artículo específico |
| `POST` | `/api/v1/graphs/{project_id}/build` | Disparar la construcción/actualización de ambos grafos |
| `GET` | `/api/v1/graphs/{project_id}/stats` | Estadísticas: nodos/aristas, artículos puente, clusters |

2. Formato de respuesta JSON compatible con vis-network:
```json
{
  "graph_type": "citation|thematic",
  "project_id": "uuid",
  "nodes": [
    {"id": "doi", "label": "Autor (Año)", "title": "...", "color": {"background": "#22c55e"}, "size": 20, "status": "included"}
  ],
  "edges": [
    {"from": "doi1", "to": "doi2", "arrows": "to", "color": "..."}
  ],
  "metadata": {"total_included": 15, "total_external": 42, "total_edges": 87}
}
```
3. Soportar filtros de query params: `?year_min=2020&year_max=2024&status=included&depth=1`.
4. Implementar paginación para grafos muy grandes (>500 nodos).

**Stack Tecnológico:**
| Tecnología | Propósito |
|-----------|-----------|
| `FastAPI` | Framework web para los endpoints REST |
| `Pydantic` v2 | Validación de schemas de respuesta |
| `NetworkX` / `Neo4j` | Backend de datos del grafo |

**Outputs:**
- Endpoints REST funcionales y documentados (OpenAPI/Swagger).
- Respuestas JSON listas para vis-network.

**QA y Métricas:**
| Métrica | Umbral Aceptable |
|---------|-----------------|
| Endpoints retornan 200 OK con datos válidos | 100% |
| Formato de respuesta compatible con vis-network | 100% |
| Latencia de respuesta para grafo de 200 nodos | < 2 s |
| Filtros por año y status funcionan correctamente | 100% |

**Tests:** `tests/integration/test_graph_api.py` (18 tests)
- Formato de respuesta del endpoint de citación
- Formato de respuesta del endpoint temático
- Colores verde/azul en nodos
- Aristas dirigidas (citación) vs no-dirigidas (temático)
- Filtros de query params

---

#### Sub-fase 4.5: Visualización Interactiva de Grafos en Frontend

**Propósito:**
Proveer una interfaz visual interactiva donde el investigador pueda explorar los dos grafos (citación y temático), hacer click en nodos para ver detalles, navegar a artículos externos (azules) para decidir si descargarlos, e identificar visualmente clusters y artículos puente.

**Argumentación Científica:**
La visualización interactiva de redes bibliográficas mejora la comprensión del panorama investigativo y permite identificar rápidamente artículos clave, tendencias emergentes y lagunas en la cobertura de la revisión. ResearchRabbit popularizó este paradigma demostrando que la exploración visual de grafos es significativamente más intuitiva que la búsqueda por keywords para descubrir literatura relacionada.

**Inputs:**
1. JSON de nodos y aristas del endpoint API (Sub-fase 4.4).
2. Selección del usuario: grafo de citación o grafo temático.

**Acciones a Realizar:**
1. Crear nueva página `/graphs?id=X` → `graphs.astro` → `GraphExplorer.tsx`.
2. Implementar **selector de tipo de grafo** (tabs o toggle): "🔗 Citaciones" vs "🧠 Temático".
3. Renderizar el grafo con **vis-network** (vis.js):
   - Layout force-directed (Barnes-Hut) con estabilización automática.
   - Nodos verdes (#22c55e) para artículos incluidos, azules (#3b82f6) para externos.
   - En el grafo temático: aristas punteadas con grosor proporcional a `cosine_similarity`.
   - En el grafo de citación: aristas con flecha direccional.
4. **Interacciones de usuario:**
   - **Click en nodo**: panel lateral desplegable con título completo, autores, año, DOI (clicable), abstract, y lista de conexiones.
   - **Click en nodo azul (externo)**: botón "📥 Buscar y descargar este artículo" que invoca las APIs de búsqueda.
   - **Hover**: tooltip con título abreviado + año.
   - **Zoom/Pan**: navegación libre con scroll y drag.
   - **Búsqueda**: campo para filtrar/resaltar nodos por keyword o autor.
5. **Panel de estadísticas** (sidebar o footer):
   - Total de nodos incluidos vs externos.
   - Top 5 artículos más citados (in-degree).
   - Clusters detectados (grafo temático).
   - Umbral de similitud ajustable (slider, solo en vista temática).
6. Botón de exportar el grafo como imagen (PNG/SVG).
7. Acceso desde el Dashboard del proyecto: nuevo botón "🕸️ Explorar Grafos".

**Sub-componentes Frontend:**

| Componente | Responsabilidad |
|-----------|----------------|
| `GraphExplorer.tsx` | Orquestador: tabs de selección, carga de datos, gestión de estado |
| `GraphVisualization.tsx` | Wrapper de vis-network: renderizado, events, physics |
| `GraphNodePanel.tsx` | Panel lateral con detalles del nodo seleccionado |
| `GraphStatsBar.tsx` | Barra de estadísticas, slider de umbral, top citados |
| `GraphToolbar.tsx` | Botones de exportar, buscar, zoom reset |

**Stack Tecnológico:**
| Tecnología | Propósito |
|-----------|-----------|
| `vis-network` (npm: `vis-network`) | Librería de grafos interactivos con force-layout |
| `vis-data` (npm: `vis-data`) | DataSets reactivos para nodos y aristas |
| React ≥ 19.x | Componentes cliente con estado |
| TailwindCSS | Estilos del panel lateral y toolbar |

**vis-network configuración de colores:**
```javascript
// Nodo incluido (VERDE)
{ color: { background: "#22c55e", border: "#16a34a",
           highlight: { background: "#4ade80", border: "#15803d" } },
  shape: "dot", size: 20 }

// Nodo externo (AZUL)
{ color: { background: "#3b82f6", border: "#2563eb",
           highlight: { background: "#60a5fa", border: "#1d4ed8" } },
  shape: "dot", size: 12 }

// Arista de citación (dirigida)
{ arrows: { to: { enabled: true, scaleFactor: 0.8 } },
  color: { color: "#94a3b8", highlight: "#f59e0b" }, width: 1.5 }

// Arista temática (no-dirigida, punteada)
{ arrows: { to: { enabled: false } },
  color: { color: "#a78bfa", highlight: "#8b5cf6" },
  width: /* proporcional a cosine_similarity */, dashes: [5, 5] }
```

**Outputs:**
- Página `/graphs?id=X` funcional con dos vistas de grafo.
- Panel lateral de detalles del nodo.
- Estadísticas y filtros interactivos.

**QA y Métricas:**
| Métrica | Umbral Aceptable |
|---------|-----------------|
| Grafo renderiza correctamente con ≤ 500 nodos | 100% |
| Click en nodo muestra panel lateral con datos correctos | 100% |
| Cambio de vista (citación ↔ temático) sin recarga de página | 100% |
| Slider de umbral actualiza el grafo en < 1 s | ≥ 95% |
| Exportar imagen funcional (PNG o SVG) | 100% |

**Flujograma:**
```mermaid
graph TD
    A["Botón 'Explorar Grafos' en ProjectDashboard"] --> B["/graphs?id=X"]
    B --> C{"Seleccionar tipo de grafo"}
    C -->|"🔗 Citaciones"| D["API: GET /graphs/{id}/citation"]
    C -->|"🧠 Temático"| E["API: GET /graphs/{id}/thematic"]
    D --> F["vis-network renderiza grafo dirigido"]
    E --> G["vis-network renderiza grafo no-dirigido"]
    F --> H{"Interacción del usuario"}
    G --> H
    H -->|Click nodo verde| I["Panel: detalles del artículo incluido"]
    H -->|Click nodo azul| J["Panel: detalles + botón descargar"]
    H -->|Hover| K["Tooltip: título + año"]
    H -->|Slider umbral| L["Recalcular aristas temáticas"]
```

**Esquema de datos de ejemplo:** Documentado en detalle con datos ficticios de 5 artículos agrícolas y sus relaciones en `docs/graph_database_schema.json`.

---

## 5. Stack Tecnológico y Requisitos del Proyecto

### 5.1 Frontend
| Tecnología | Versión | Propósito |
|-----------|---------|-----------|
| **Astro** | ≥ 5.x | Framework web con islas interactivas (partial hydration) |
| **React** (o Solid.js) | ≥ 19.x | Componentes cliente interactivos (Chat, Screening cards) |
| **TailwindCSS** | ≥ 4.x | Sistema de diseño rápido y consistente |
| **Shadcn/UI** | - | Componentes accesibles pre-construidos |

### 5.2 Backend
| Tecnología | Versión | Propósito |
|-----------|---------|-----------|
| **Python** | ≥ 3.11 | Lenguaje principal del backend |
| **FastAPI** | ≥ 0.115 | Framework web asíncrono para APIs REST |
| **SQLAlchemy** | ≥ 2.x | ORM para la base de datos relacional |
| **Alembic** | - | Migraciones de base de datos |
| **SQLite** | - | Base de datos relacional local (sin servidor) |
| **Pydantic** | ≥ 2.x | Validación de datos y schemas |
| **aiohttp** | - | Cliente HTTP asíncrono para descargas |

### 5.3 LLMs y RAG
| Tecnología | Propósito |
|-----------|-----------|
| **Ollama** | Servidor local de LLMs (llama3, mistral, nomic-embed-text) |
| **LiteLLM** (https://github.com/BerriAI/litellm) | Capa de abstracción agnóstica de proveedores LLM |
| **Qdrant** | Base de datos vectorial local (persistida en disco) |
| **rank_bm25** | Índice BM25 para retrieval complementario |
| **pymupdf4llm** | Extracción robusta de texto de PDFs |
| **nomic-embed-text** (vía Ollama) | Modelo de embeddings local (768 dim) |

### 5.4 MCPs (Model Context Protocol Servers)
| Servidor MCP | Propósito |
|-------------|-----------|
| `openalex-mcp-lite` | Búsqueda en OpenAlex (>200M works) |
| `research-semantic-scholar` | Búsqueda en Semantic Scholar |
| `arxiv-mcp-server` | Búsqueda en ArXiv |
| `browsermcp` | Búsqueda web de respaldo (Google Scholar, manuales) |

### 5.5 Grafos y Visualización (Fase 4)
| Tecnología | Versión | Propósito |
|-----------|---------|-----------|
| **NetworkX** | ≥ 3.x | Biblioteca Python para grafos en memoria (cita + temático) |
| **Neo4j Community** (opcional) | ≥ 5.x | Base de datos de grafos con Cypher para queries complejas |
| **neo4j-python-driver** (opcional) | ≥ 5.x | Conector Python → Neo4j (si se usa Neo4j) |
| **vis-network** (npm) | ≥ 9.x | Visualización frontend interactiva de grafos force-directed |
| **vis-data** (npm) | ≥ 7.x | DataSets reactivos para nodos y aristas |
| **scikit-learn** | ≥ 1.x | Cálculo de `cosine_similarity` para el grafo temático |
| **GROBID** (Docker, opcional) | ≥ 0.8 | Parser de bibliografías de PDFs científicos |

### 5.6 Calidad y Seguridad (Clean Code)
| Herramienta | Propósito |
|------------|-----------|
| **Ruff** | Linter + formatter ultrarrápido para Python |
| **Mypy** | Type checking estático |
| **Pytest** | Testing unitario e integración |
| **Bandit** | Detección de vulnerabilidades de seguridad en Python |
| **Safety** | Auditoría de dependencias vulnerables |
| **Pre-commit hooks** | Ejecutar linting/typing/security antes de cada commit |

### 5.7 Requisitos del Sistema del Usuario
- **RAM:** ≥ 16 GB (recomendado 32 GB para modelos LLM grandes)
- **GPU:** Opcional pero recomendada (NVIDIA con ≥ 8 GB VRAM para Ollama)
- **Disco:** ≥ 50 GB libres para PDFs, vectores y modelos
- **Ollama instalado:** Con modelos descargados (`llama3.1:8b`, `nomic-embed-text`)
- **Node.js:** ≥ 20.x (para el frontend Astro)
- **Python:** ≥ 3.11

---

## 6. Ideas de Mejora Adicionales

1. **Diagrama PRISMA interactivo y auto-generado:** Que se actualice en tiempo real conforme avanzan las fases y pueda exportarse como SVG/PDF para incluir en publicaciones.
2. **Multi-usuario (futuro):** Soporte para que dos o más revisores hagan screening en paralelo con resolución de conflictos (similar a la funcionalidad de blind screening de Rayyan).
3. **Integración con Zotero/Mendeley:** Importar/exportar referencias al gestor bibliográfico del usuario.
4. **AGROVOC autosugerido:** Integrar la API del tesauro AGROVOC de la FAO para sugerir términos controlados específicos al dominio agrícola.
5. **Modo "Quick Review":** Para cuando el usuario no quiere una revisión sistemática completa sino una búsqueda rápida exploratoria sobre un tema.
6. **Dashboard analítico:** Gráficos de distribución por año, por tema, por autor más citado, word clouds de keywords.
7. **Exportación PRISMA Checklist:** Generar automáticamente el checklist de 27 ítems de PRISMA 2020 con los datos del proyecto.
8. **Soporte multi-idioma del corpus:** Poder indexar artículos en español, portugués e inglés simultáneamente.

---

## 7. Referencias Bibliográficas

- Aubin, S., Hamon, T., & Nazarenko, A. (2006). AGROVOC Term Extraction for Ontology Learning. *Natural Language Processing and Information Systems*, 3999, 1-12. https://doi.org/10.1007/11765448_1

- Gao, Y., Xiong, Y., Gao, X., Jia, K., Pan, J., Bi, Y., Dai, Y., Sun, J., Wang, M., & Wang, H. (2024). Retrieval-Augmented Generation for Large Language Models: A Survey. *arXiv preprint*. https://doi.org/10.48550/arXiv.2312.10997

- Higgins, J. P. T., Thomas, J., Chandler, J., Cumpston, M., Li, T., Page, M. J., & Welch, V. A. (Eds.). (2019). *Cochrane Handbook for Systematic Reviews of Interventions* (2nd ed.). John Wiley & Sons. https://doi.org/10.1002/14651858.ED000142

- Hosseini, M., Rasmussen, L. M., & Resnik, D. B. (2023). Using AI to write scholarly publications. *Accountability in Research*, 1-9. https://doi.org/10.1080/08989621.2023.2168535

- Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *Advances in Neural Information Processing Systems*, 33, 9459-9474. https://doi.org/10.48550/arXiv.2005.11401

- Miwa, M., Thomas, J., O'Mara-Eves, A., & Ananiadou, S. (2014). Reducing systematic review workload through certainty-based screening. *Journal of Biomedical Informatics*, 51, 242-253. https://doi.org/10.1016/j.jbi.2014.06.005

- Ouzzani, M., Hammady, H., Fedorowicz, Z., & Elmagarmid, A. (2016). Rayyan—a web and mobile app for systematic reviews. *Systematic Reviews*, 5(1), 210. https://doi.org/10.1186/s13643-016-0384-4

- Page, M. J., McKenzie, J. E., Bossuyt, P. M., Boutron, I., Hoffmann, T. C., Mulrow, C. D., Shamseer, L., Tetzlaff, J. M., Akl, E. A., Brennan, S. E., Chou, R., Glanville, J., Grimshaw, J. M., Hróbjartsson, A., Lalu, M. M., Li, T., Loder, E. W., Mayo-Wilson, E., McDonald, S., ... & Moher, D. (2021). The PRISMA 2020 statement: An updated guideline for reporting systematic reviews. *BMJ*, 372, n71. https://doi.org/10.1136/bmj.n71

- van de Schoot, R., de Bruin, J., Schram, R., Berber, P., Frontalini Rekers, S., Kramer, B., Huijts, C., Hoogervorst, L., Ferdinands, G., Harkema, A., & Oelen, A. (2021). An open source machine learning framework for efficient and transparent systematic reviews. *Nature Machine Intelligence*, 3, 125-133. https://doi.org/10.1038/s42256-020-00287-7

- Skidmore, B., & Greyson, D. (2023). CADTH Search Methods for Literature Reviews. *CADTH Methods and Guidelines*. https://doi.org/10.51731/cjht.2023.702

- Brack, A., Hoppe, A., & Ewerth, R. (2021). Citation Recommendation for Research Papers via Knowledge Graphs. *Lecture Notes in Computer Science*, vol 12656. Springer. https://doi.org/10.48550/arXiv.2106.05633

- Jia, H., & Saule, E. (2018). Towards Finding Non-obvious Papers: An Analysis of Citation Recommender Systems. *arXiv preprint*. https://doi.org/10.48550/arXiv.1812.11252

- Maharjan, P. (2024). Benchmark for Evaluation and Analysis of Citation Recommendation Models. *arXiv preprint*. https://doi.org/10.48550/arXiv.2412.07713

---

*Documento generado el 22 de febrero de 2026. Última actualización: 5 de abril de 2026. Versión 4.0.*
*Proyecto: AgriSearch — Chat Búsqueda Sistemática*
