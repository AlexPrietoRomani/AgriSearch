# Documentación Técnica - AgriSearch

Este documento contiene el registro de cambios funcionales, decisiones técnicas, flujos de datos relevantes y posibles errores para mantener la trazabilidad de la aplicación AgriSearch.

---

## Registro de Cambios y Funcionalidades

### Búsqueda y Obtención de PDFs (Fase 1)
- **Extracción Inteligente:** Ejecuta queries a OpenAlex, Semantic Scholar y Arxiv, deduplica e inserta en SQLite.
- **Adaptación Determinista por Base de Datos:** Para evitar fallos de sintaxis en búsquedas complejas (ej. consultas booleanas con paréntesis que rompen las APIs), el backend usa un módulo determinista (`query_builder.py`) que construye la query óptima para cada API. No depende de un LLM para la adaptación, eliminando la impredecibilidad.
  - **OpenAlex**: Texto plano con keywords separados por espacios.
  - **Semantic Scholar**: Keywords concisas (no acepta nested boolean logic).
  - **ArXiv**: Formato `all:"concepto1" AND all:"concepto2"` con sinónimos agrupados por OR.
  - **Crossref**: Keywords separados por espacio, API via `habanero` (no requiere key).
  - **CORE**: Keywords con filtros de año, requiere API key gratuita.
  - **SciELO**: Keywords multilingüe (es/en/pt), API libre.
  - **Redalyc**: Keywords con token, ideal para Iberoamérica.
  - **AgEcon Search**: OAI-PMH libre, filtrado local por keywords.
  - **Organic Eprints**: OAI-PMH libre, filtrado local por keywords.
- **Extracción de Conceptos por LLM:** El LLM (Ollama) se usa **solo una vez** para extraer conceptos, sinónimos y desglose PICO del input del usuario. Retorna un JSON estructurado (no una query booleana libre).
- **Descarga Múltiple Open Access:** El servicio `download_service.py` obtiene automáticamente los PDFs vía requests asíncronas de las URLs enlazadas, los guarda en `data/projects/{id}/pdfs` y los nombra automáticamente usando la convención `[Año]_[PrimerAutor]_[Slug_Titulo].pdf`.
- **Subida Manual (Upload):** Endpoint `POST /search/upload-pdf/{article_id}`. Para los artículos que están bloqueados por un paywall, el usuario puede subir localmente su archivo PDF desde el dashboard de resultados. El archivo se enlaza directamente a su base de datos.
- **Eliminación de Búsquedas Segura:** Los usuarios pueden eliminar consultas del historial preventivamente. Esta acción ejecuta un Cascade Delete en la base de datos (eliminando `SearchQuery` y sus `Article`s) e intercepta el almacenamiento local, eliminando automáticamente los archivos PDF asociados a tales IDs para liberar espacio en disco. En la UI, el botón de eliminación está correctamente posicionado por encima del bloque redireccionador (con `z-index` y `stopPropagation`) para evitar colisiones de clics.
- **Transparencia Total de Queries:** `ArticleResponse` incluye `local_pdf_path` para que el frontend pueda mostrar el nombre del archivo local en la tabla de resultados. `SearchResultsResponse` incluye la propiedad `prompt_used` y `adapted_queries` con precisión literal. Además se ha modificado la tabla `SearchQuery` en SQLite (añadiendo la columna en texto plano `adapted_queries_json`) para preservar perennemente qué le fue enviado a cada API. En la Interfaz de Resultados, un Acordeón desplegable de "Depuración" expone ambos parámetros al investigador.
- **Dashboard Integrado:** La portada de cada proyecto (`ProjectDashboard.tsx`) amalgama eficientemente tanto el **Historial de Búsquedas** como el **Historial de Revisiones (Screening)**, creando un ecosistema completo para monitorear el progreso del cribado PRISMA en una sola vista central. Asimismo se han refactorizado las asignaciones de estado (`useState`) iniciales en base a parámetros URl para eliminar destellos visuales o pestañeos transaccionales del renderizado (Flicker Fixes).

#### Flujo de Búsqueda (Diagrama de Secuencia)

```mermaid
sequenceDiagram
    actor User as Usuario
    participant FE as Frontend
    participant API as FastAPI
    participant LLM as LLM (Ollama)
    participant QB as query_builder.py
    participant OA as OpenAlex
    participant SS as Semantic Scholar
    participant AX as ArXiv
    participant DB as SQLite

    User->>FE: Describe tema en lenguaje natural
    FE->>API: POST /build-query
    API->>LLM: Extrae conceptos + sinónimos + PICO
    LLM-->>API: {concepts, synonyms, pico}
    API-->>FE: Conceptos para revisión del usuario
    User->>FE: Aprueba/edita query
    FE->>API: POST /execute {query, databases}
    API->>QB: build_all_queries(concepts, databases)
    QB-->>API: {openalex: "...", ss: "...", arxiv: "..."}
    par OpenAlex
        API->>OA: GET /works?search=...
    and Semantic Scholar
        API->>SS: GET /paper/search?query=...
    and ArXiv
        API->>AX: GET /api/query?search_query=...
    end
    OA-->>API: resultados
    SS-->>API: resultados
    AX-->>API: resultados
    API->>API: Merge + Dedup (DOI + fuzzy title)
    API->>DB: INSERT artículos nuevos
    API-->>FE: Resultados + adapted_queries
    FE->>User: Tabla de artículos filtrados
```

#### Archivos clave del flujo
| Archivo | Responsabilidad |
|---------|----------------|
| `services/query_builder.py` | Genera queries deterministas para las 9 APIs |
| `services/llm_service.py` | Extrae conceptos del input (solo 1 llamada LLM) |
| `services/search_service.py` | Orquesta búsqueda paralela, dedup y almacenamiento |
| `services/mcp_clients/openalex_client.py` | Cliente OpenAlex REST API |
| `services/mcp_clients/semantic_scholar_client.py` | Cliente Semantic Scholar API |
| `services/mcp_clients/arxiv_client.py` | Cliente ArXiv Atom API |
| `services/mcp_clients/crossref_client.py` | Cliente Crossref via `habanero` |
| `services/mcp_clients/core_client.py` | Cliente CORE API v3 |
| `services/mcp_clients/scielo_client.py` | Cliente SciELO Search API |
| `services/mcp_clients/redalyc_client.py` | Cliente Redalyc REST API |
| `services/mcp_clients/oaipmh_client.py` | Cliente OAI-PMH (AgEcon + Organic Eprints) |

#### Bases de datos — Resumen de acceso
| Base | Tipo | API Key | Link de registro |
|------|------|---------|------------------|
| OpenAlex | REST | Opcional (gratis) | [openalex.org](https://openalex.org/settings/api) |
| Semantic Scholar | REST | Opcional (gratis) | [semanticscholar.org](https://www.semanticscholar.org/product/api) |
| ArXiv | Atom/REST | No | — |
| Crossref | REST (`habanero`) | No (email recomendado) | — |
| CORE | REST v3 | Sí (gratis) | [core.ac.uk](https://core.ac.uk/api-keys/register) |
| SciELO | REST | No | — |
| Redalyc | REST | Sí (gratis) | [redalyc.org](https://redalyc.org) |
| AgEcon Search | OAI-PMH | No | — |
| Organic Eprints | OAI-PMH | No | — |

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
| `/screening/sessions/{session_id}/articles/{article_id}/pdf` | GET | Retorna el archivo PDF asociado en formato `application/pdf` |
| `/screening/decisions/{decision_id}` | PUT | Actualizar decisión (include/exclude/maybe) |
| `/screening/translate` | POST | Traducir abstract vía LLM |
| `/screening/enrich/{project_id}` | POST | Enriquecimiento pre-screening desde PDFs |
| `/screening/sessions/{session_id}/articles/{article_id}/suggestion` | GET | Obtener sugerencia IA de relevancia (AI Assist) |

#### Flujo del Frontend (`ScreeningSetup.tsx`)
1. Al entrar a `/screening?id=X`, se verifica si hay sesión existente.
2. **Si hay sesión:** Muestra tarjeta resumen con estadísticas → Continuar o Eliminar.
3. **Si no hay:** Formulario de creación con nombre, objetivo, selección de búsquedas, idioma y modelo.
4. Al crear, ejecuta enriquecimiento automático (PyMuPDF) y luego crea la sesión (filtrada solo PDFs).

#### Pantalla Previa `ScreeningSetup`
- Permite elegir qué consultas integrar en el proceso actual y con qué modelo traducir los resúmenes.
-    *   **Enriquecimiento Automático:** Se mejoró sustancialmente la extracción de abstracts desde PDFs en `pdf_enrichment_service.py`. En caso de no hallar formalmente el *Abstract* con regex debido a PDFs sin un formato estándar (proceedings, revistas antiguas), se extrae inteligentemente el primer bloque extenso o un pasaje limpio inicial, reemplazando con éxito textos previos demasiado breves, resolviendo fallas con algunos archivos MCP.
    *   **Traducción de Abstracts**: Se llama a LLMs en tiempo real para traducir la versión enriquecida del abstract del PDF, sin depender de datos faltantes iniciales. Es posible elegir el modelo de LLM al crear **o continuar** una sesión de screening.
#### Proceso Interactivo (`ScreeningSession`)
Interfaz interactiva para screening:
- **Botones de decisión**: "Incluir", "Excluir" (con sub-razones), "Tal vez".
- **Visualizador Integrado**: Mediante el botón "Ver PDF" (atajo `P`), se invoca el endpoint `/pdf` para renderizar el documento PDF mediante un iframe de tamaño adaptable en la misma pantalla.
- **Asistencia Inteligente (AI Assist)**: Después de 10 decisiones manuales, el sistema genera sugerencias de inclusión/exclusión usando *Few-shot learning*. El LLM analiza el progreso y ayuda a mantener consistencia en los criterios.
- **Formateos automáticos**: Autores largos se truncan y abstracts se traducen con Ollama local.

#### Soporte Multi-Screening (Revisiones)
El sistema ahora soporta formalmente la creación de **múltiples sesiones de screening concurrentes** en un mismo proyecto. 
Esto permite que varias personas trabajen simultáneamente dividiéndose los artículos.
- Al hacer clic en "Revisiones" dentro del Dashboard, un endpoint de validación (`GET /eligibility/{project_id}`) verifica cuántos artículos que fueron descargados con éxito (`SUCCESS`) aún están libres de asignación.
- **Visualización Condicional**: En la pantalla de creación, se ocultan del listado aquellas búsquedas que ya completaron la asignación de todos sus artículos (es decir, aquellas con 0 artículos pendientes por evaluar). Las tarjetas de búsqueda muestran detalladamente la numeración original, prompt usado, artículos totales, duplicados y finalmente los "descargados por revisar".
- **Lógica Estricta de Asignación (OuterJoin)**: Al registrar la sesión final, el backend cruza la base de datos (con `outerjoin`) para extraer matemáticamente SOLO los artículos elegibles exentos de participar en otra revisión activa. Ningún artículo se repetirá a través de múltiples revisiones.
- **Nombres Automáticos:** El campo de "nombre de la sesión" ahora sugiere secuencias inteligentes opcionales ("Revisión 1", "Revisión 2") y el "Objetivo" es estrictamente prescindible.
- **Regla de Bloqueo General**: Si todos los artículos exitosos del proyecto ya están aglomerados en las sesiones existentes, el sistema levanta una alerta gráfica (Popup) impidiendo la creación de una revisión vacía y exigiendo realizar más búsquedas previamente.
- **Control de Colisiones en Base de Datos (Estrategia UUID)**: En el sistema backend, todos los modelos (`projects`, `search_queries`, `articles`, `screening_sessions`, `screening_decisions`) utilizan `UUIDv4` como Clave Primaria inmutable (`String`). Esta decisión arquitectónica avala que es computacional y probabilísticamente imposible que un artículo o revisión de un proyecto sufra una "colisión de IDs" (cruce de información) con sesiones o artículos de otro proyecto, blindando la integridad referencial.

#### Arquitectura de Base de Datos y Diccionarios Funcionales (`/docs`)
La robustez contra duplicados intra e inter APIs, revisiones concurrentes e inmutabilidad multi-usuario descansa en un modelado de Base de Datos robusto documentado explícitamente en tres artefactos fundacionales:
1. `docs/database_schema_expected.json`: Diccionario canónico que delimita el objetivo, tipo de dato y restricciones SQL lógicas (Ejemplo y Explicación) sobre cada tabla de `agrisearch.db`.
2. `docs/database_schema_current.json`: Snapshot auto-generado de SQLite usando pragmas para evidenciar el estado 1:1 real del servidor.
3. `docs/database_diagram.md`: Diagrama de Arquitectura ER (Entity Relationship) escrito nativamente en código `mermaid`. Ilustra el proceso de cómo 1 Proyecto se ramifica atando fuertemente el destino de una "Búsqueda" o "Revisión" hasta las múltiples "Decisiones PRISMA" usando UUIDs.
---

## Dependencias Críticas
- **PyMuPDF**: Necesario en el backend para la extracción limpia de texto de archivos PDF durante la fase pre-screening. (`pip install PyMuPDF`).
- **Ollama**: Requiere tener en ejecución instancias de modelos LLM. Por ejemplo, `aya-expanse` como opción multilingüe óptima de 8B.

## Modelos LLM Sugeridos (Ollama)
1. **Aya 8B (`aya:8b`)** — Recomendado. Modelo multilingüe optimizado de Cohere. Excelente para traducciones EN↔ES/PT.
2. **Llama 3.1 8B (`llama3.1:8b`)** — Rendimiento general sólido.
3. **Qwen 2.5 7B (`qwen2.5:7b`)** — Alternativa rápida y eficiente.

> **Nota:** Se utiliza `aya:8b` como tag preferente por su disponibilidad y rendimiento estable en entornos locales.

## UI/UX Global
- **Modo claro/oscuro:** Toggle global persistente (localStorage) en la barra de navegación, disponible en todas las páginas.

---

*Nota: Este documento debe ser actualizado iterativamente al realizar modificaciones importantes, en cumplimiento con el flujo `update-documentation.md`.*
