# AgriSearch 🌱

**AgriSearch** es una plataforma de **Búsqueda Sistemática y Asistente de Investigación Agrícola** diseñada para automatizar, agilizar y optimizar las fases de revisión bibliográfica y extracción de datos en investigaciones académicas, basándose estrictamente en las directrices de reporte **PRISMA 2020**.

El sistema integra **9 Bases de Datos Científicas** y Modelos de Lenguaje Grandes (LLMs) (vía Ollama/LiteLLM) en Arquitecturas de Generación Aumentada por Recuperación (RAG).

### Bases de Datos Integradas

| Base | Tipo | API Key |
|------|------|---------|
| OpenAlex | REST | Opcional (gratis) |
| Semantic Scholar | REST | Opcional (gratis) |
| ArXiv | Atom/REST | No |
| Crossref | REST (`habanero`) | No |
| CORE | REST v3 | Sí (gratis) |
| SciELO | REST | No |
| Redalyc | REST | Sí (gratis) |
| AgEcon Search | OAI-PMH | No |
| Organic Eprints | OAI-PMH | No |

> 📌 Ver `backend/.env.example` para instrucciones de registro y links.

### Flujo de Búsqueda

1. **Describir** — El usuario describe su tema en lenguaje natural.
2. **Elegir Modelo** — Selecciona un modelo optimizado para GPU (ej. `llama3.1:8b`) o CPU (ej. `phi3:3.8b`), o ingresa uno manualmente.
3. **Extraer conceptos** — Un LLM local (Ollama) extrae conceptos clave, sinónimos y desglose PICO/PEO.
4. **Construir queries** — Un módulo determinista (`query_builder.py`) genera la query óptima para cada API, sin depender de un LLM para la adaptación.
4. **Buscar en paralelo** — Las queries se ejecutan concurrentemente contra las 9 bases de datos.
5. **Deduplicar** — Se eliminan duplicados por DOI y título (fuzzy matching ≥85%).
6. **Presentar** — El usuario ve los resultados en una tabla interactiva con la query enviada a cada API para transparencia.

---

## 🚀 Tecnologías Principales

*   **Frontend**: Astro (SSR Híbrido), React, CSS Vanilla (Vite).
*   **Backend**: FastAPI (Python 3.11), SQLAlchemy, aiosqlite (SQLite local).
*   **Parsing de Documentos**: OpenDataLoader PDF (artículos científicos, #1 en benchmarks), Microsoft MarkItDown (DOCX, PPTX, XLSX, HTML, EPUB).
*   **IA e Integración**: LiteLLM, Ollama, Qdrant (Base de datos Vectorial local).
*   **Gestión de Agentes**: Herramientas integradas en Model Context Protocol (MCP) creados para interconectar búsquedas en la web y descargar referencias.
*   **Gestión de Dependencias**: [uv](https://docs.astral.sh/uv/) (recomendado) o pip como alternativa.

## 📥 Estructura del Proyecto

El proyecto está separado en dos contenedores lógicos principales:

1.  `/backend`: Lógica del servidor, API REST (FastAPI), modelos Pydantic, conexión a bases de datos SQLite y Qdrant, y procesamiento RAG/LLM.
2.  `/frontend`: Interfaz de usuario (Astro SSR híbrido + React para componentes dinámicos de cliente), estilizada con CSS Vanilla.

## 🛠 Instalación y Ejecución Local

### Requisitos Previos

| Requisito | Versión | Propósito |
|-----------|---------|-----------|
| **Python** | 3.11.x | Backend (FastAPI) |
| **Node.js** | 18+ | Frontend (Astro) |
| **Java (JDK)** | 11+ | OpenDataLoader PDF (parser de artículos científicos) |
| **Ollama** | Última | LLM local para búsqueda asistida y screening |
| **uv** *(recomendado)* | Última | Gestión de dependencias Python (alternativa: pip) |

> ⚠️ **Java es necesario** para el parsing de PDFs científicos con OpenDataLoader PDF. Verifica con `java -version`. Si no lo tienes, instálalo desde [Adoptium](https://adoptium.net/).

> ⚠️ **Ollama debe estar ejecutándose** para que AgriSearch pueda orquestar las búsquedas y asistir en el cribado.

Para la configuración detallada de los modelos, descarga y optimización (CPU vs GPU), por favor consulta primero la **[Guía de Ejecución (ejecucion.md)](ejecucion.md)**.

A continuación el **Modelo Generalista** recomendado según tu perfil de hardware:

| Perfil | Hardware | Modelo Ideal | Comando |
| :--- | :--- | :--- | :--- |
| **CPU Baja** | < 8GB RAM | `gemma2:2b` | `ollama pull gemma2:2b` |
| **CPU Media** | 16GB RAM | `phi4-mini:3.8b`| `ollama pull phi4-mini:3.8b`|
| **CPU Alta** | 32GB+ RAM | `gemma4:e4b` | `ollama pull gemma4:e4b` |
| **GPU Baja** | 4GB VRAM | `qwen2.5:3b` | `ollama pull qwen2.5:3b` |
| **GPU Media** | 8GB VRAM | `llama3.1:8b` | `ollama pull llama3.1:8b` |
| **GPU Alta** | 16GB VRAM | `gemma4:e4b` | `ollama pull gemma4:e4b` |
 
> 📊 **Matriz de Especialidad Avanzada:** Para configuraciones optimizadas por tarea basándose en benchmarks (MMLU, Human-Eval), consulta la **[Matriz de 24 Modelos con Métricas y RAM](docs/documentation.md#2-matriz-de-especialidad-24-modelos-recomendados)**.

*(Mantén Ollama corriendo en segundo plano antes de iniciar la aplicación).*

### ▶️ Ejecución Rápida (Recomendado para Windows)
Hemos incluido un script inteligente en la raíz del proyecto para facilitar el arranque y **su primera ejecución**.

Simplemente haz doble clic en el archivo:
> `start_agrisearch.bat`

Al hacer esto por primera vez, el script se encargará automáticamente de:
- Verificar o instalar el entorno virtual en `backend/` usando `uv` (o recurriendo a `pip` tradicional si no tienes `uv` instalado).
- Descargar e instalar todas las dependencias de Python y Node (`npm install`).
- Crear las carpetas de datos locales para SQLite y Qdrant.
- Abrir las terminales independientes y lanzar el navegador.

---

### Instalación Manual Paso a Paso

> 💡 **Nota:** Para una guía visual y detallada paso a paso, por favor lee **[ejecucion.md](ejecucion.md)**.

#### 1. Configuración del Backend (con `uv` — Recomendado)

```bash
cd backend
uv sync                                    # Crea el .venv e instala todas las dependencias
uv run uvicorn app.main:app --port 8000    # Inicia el servidor
```

#### 1b. Configuración del Backend (con `pip` — Alternativa)

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate   # En Windows
pip install -e .           # Instala desde pyproject.toml
uvicorn app.main:app --port 8000
```

La API estará disponible en `http://localhost:8000` (documentación Swagger en `/docs`).

#### 2. Configuración del Frontend

1. Abre una nueva terminal y navega al directorio del frontend:
   ```bash
   cd frontend
   ```
2. Instala las dependencias NPM:
   ```bash
   npm install
   ```
3. Inicia el servidor de desarrollo Astro:
   ```bash
   npm run dev
   ```
La plataforma estará disponible en `http://localhost:4321`.

---

## 📝 Documentación Interna

Puedes encontrar el roadmap y proceso de planeamiento completo de diseño en el archivo [`plan_a_seguir.md`](plan_a_seguir.md).

Para consultar el registro técnico de cada funcionalidad implementada, revisa [`documentation.md`](documentation.md).

En la carpeta `.agents/workflows/` encontrarás reglas definidas de comportamiento de commits y creación de nuevos endpoints/pantallas para la estandarización de código.

### 🔬 Screening (Cribado PRISMA)

Una vez completada la búsqueda y descarga de PDFs, el módulo de **Screening** permite:

- **Sesión con identidad:** Cada sesión tiene un nombre y objetivo definidos por el usuario.
- **Solo artículos con PDF:** Únicamente los artículos cuyo PDF fue descargado exitosamente entran al screening.
- **1 sesión activa por proyecto:** Si ya existe, el usuario puede continuar o eliminarla para crear una nueva.
- **Extracción de Abstract desde PDF:** Extrae y corrige el abstract leyendo directamente el documento PDF descargado si el proporcionado por la API es insuficiente o erróneo.
- **Visualizador PDF integrado:** Permite ver el documento completo sin salir de la interfaz, mediante un iframe in-app, sin problemas de extensiones que forzaban descarga gracias a inline disposition headers.
- **Traducción automática de abstracts:** Vía modelos Ollama locales configurables (`gemma4:e4b`, `llama3.1:8b`, `qwen2.5:7b`), actualizables durante la fase iterativa de cribado o al continuar sesiones antiguas.
- **Decisiones PRISMA:** Incluir / Excluir (con motivo) / Tal Vez, con atajos de teclado completos (incluye "P" para abrir/cerrar PDF).
- **Vista dual:** Tarjeta individual o tabla completa con todos los artículos.

## 🧑‍💻 Autoría

Desarrollado y mantenido por **ALEX** (@alex).

## 📄 Licencia

Este proyecto se distribuye bajo la licencia **MIT**. Eres libre de usar, modificar y distribuir el código, manteniendo siempre el reconocimiento al autor original.
Licencia abierta con fines investigativos y educativos.
