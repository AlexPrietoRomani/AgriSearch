# Arquitectura de Base de Datos - Agrisearch

El sistema backend de AgriSearch utiliza **SQLite** y el framework ORM **SQLAlchemy** (modo asíncrono con `aiosqlite`). 
La arquitectura prioriza en un 100% la aislación e integridad de datos usando llaves principales `UUIDv4`, logrando una estructura descentralizada inmune a colisiones de inter-proyectos y multi-sesiones. 

## Diagrama Entidad-Relación (ER Diagram)

El siguiente diagrama Mermaid ilustra la jerarquía y cómo se propaga la recolección desde la entidad Raíz `Project` hasta el último veredicto de decisión (`Screening Decision`).

```mermaid
erDiagram
    Project ||--o{ SearchQuery : "ejecuta y almacena"
    Project ||--o{ Article : "contiene recolectados"
    Project ||--o{ ScreeningSession : "asigna a miembros"
    
    SearchQuery ||--o{ Article : "descubre (1 a N)"
    
    Article ||--o{ ScreeningDecision : "recibe veredicto de"
    ScreeningSession ||--o{ ScreeningDecision : "componen la iteración UI"

    Project {
        UUID id PK "UUIDv4 inmutable"
        VARCHAR name "Nombre Proyecto"
        TEXT description "Propósito"
        VARCHAR agri_area "Agricultura de Precisión..."
        VARCHAR language "BCP-47 idioma"
        DATETIME created_at 
    }

    SearchQuery {
        UUID id PK "UUIDv4"
        UUID project_id FK "Pertenece al Proyecto"
        TEXT raw_input "Prompt NLP Original"
        TEXT generated_query "Query PICO Boolena final"
        VARCHAR databases_used "Lista sources: arxiv,openalex"
        TEXT adapted_queries_json "Metadatos crudos generados para cada API"
        INTEGER total_results "Impacto de indexación cruda"
        INTEGER duplicates_removed "Eliminado intra y cros API"
    }

    Article {
        UUID id PK "UUIDv4 Global"
        UUID project_id FK "Atado a Proyecto (Obligatorio)"
        UUID search_query_id FK "La 1° Query que trajo el paper (Relativo)"
        VARCHAR doi "DOI 10.1030/... (Único teórico)"
        TEXT title "Abstract Text o HTML limpio"
        VARCHAR authors "Wang et al., Smith V."
        INTEGER year "2024"
        TEXT abstract "Extracción Textual original API"
        VARCHAR source_database "openalex/arxiv/crossref/semantic"
        BOOLEAN is_duplicate "True/False Control Interno"
        VARCHAR duplicate_of_id "Si es dupe, ancla a quién"
        VARCHAR download_status "Enum: PENDING, SUCCESS, FAILED"
        VARCHAR local_pdf_path "System FilePath"
    }

    ScreeningSession {
        UUID id PK "UUIDv4"
        UUID project_id FK "Atado a Proyecto"
        VARCHAR name "Revisión 1/Revisión 2"
        TEXT goal "Objetivo Específico PRISMA"
        TEXT search_query_ids "JSON Lista Array de las queries elegidas en UI"
        VARCHAR translation_model "Cohere, Llama o Qwen"
        INTEGER total_articles "Sumatoria PENDING"
        INTEGER reviewed_count "Conteo Volátil actual UI"
        INTEGER included_count "Verdes"
        INTEGER excluded_count "Rojos"
    }

    ScreeningDecision {
        UUID id PK "UUIDv4 de la Decisión"
        UUID session_id FK "A qué Revisión pertenece"
        UUID article_id FK "Qué Artículo Original evalúa"
        VARCHAR decision "Enum: PENDING, INCLUDE, EXCLUDE, MAYBE"
        VARCHAR exclusion_reason "Enum Sub Razón Ej: Outh of Scope"
        TEXT reviewer_note "Recordatorios de texto libre"
        TEXT translated_abstract "Abstract LLM en el Cache de idioma nativo (reading_language)"
        INTEGER display_order "Secuencia Index para la IU en Tarjetas"
    }
```

## Relación Dinámica de Sesiones y Limitaciones

Una base principal del sistema AgriSearch es el **Blindaje Anti-Repeticiones** para metodologías PRISMA:

1. **Un solo Artículo Múltiples Búsquedas:** Si la Búsqueda 1 baja un paper de YOLO por Arxiv, y la Búsqueda 2 halla exactamente el mismo paper por OpenAlex, la capa backend detecta por similitud de DOI/título y setea `is_duplicate=True` atando este hallazgo inoperante (`duplicate_of_id`) al hallazgo maestro del origen original. El artículo duplicado no podrá participar de Screening.
2. **Revisión Continua Multi-Agente (Screening):** Al crear una `ScreeningSession`, se invoca un SQL Outer Join masivo para identificar artículos de `project_id` que **tengan éxito en PDF**, **no sean is_duplicate** y que **no existan** sus UUID combinados en la tabla `screening_decisions`. 
3. **Generación Instantánea de Decisiones:** La inicialización UI crea un registro masivo de `ScreeningDecision(status=PENDING)` para anclarlos irrompiblemente a esa Revisión, impidiendo lógicamente que al mismo tiempo, en otra pestaña u otro computador, alguien pueda "Re-Revisar" la misma porción de artículos ya pre-reservados. Múltiples analistas pueden trabajar concurrentemente en un mismo Proyecto de la mano de UUIDs matemáticamente invulnerables.
