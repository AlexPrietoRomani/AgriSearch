# AgriSearch 🌱

**AgriSearch** es una plataforma de **Búsqueda Sistemática y Asistente de Investigación Agrícola** diseñada para automatizar, agilizar y optimizar las fases de revisión bibliográfica y extracción de datos en investigaciones académicas, basándose estrictamente en las directrices de reporte **PRISMA 2020**.

El sistema integra Motores de Búsqueda Académicos (OpenAlex, Semantic Scholar, ArXiv) y Modelos de Lenguaje Grandes (LLMs) (vía Ollama/LiteLLM) en Arquitecturas de Generación Aumentada por Recuperación (RAG).

> ⚠️ **Estado del Proyecto:** En fase de desarrollo y creación (fase Alpha). Se está implementando el Search Wizard y la conectividad base. El código puede contener errores y cambiar en cualquier momento.

---

## 🚀 Tecnologías Principales

*   **Frontend**: Astro, React, Tailwind CSS (Vite).
*   **Backend**: FastAPI (Python), SQLAlchemy, aiosqlite (SQLite local).
*   **IA e Integración**: LiteLLM, Ollama, Qdrant (Base de datos Vectorial local).
*   **Gestión de Agentes**: Herramientas integradas en Model Context Protocol (MCP) creados para interconectar búsquedas en la web y descargar referencias.

## 📥 Estructura del Proyecto

El proyecto está separado en dos contenedores lógicos principales:

1.  `/backend`: Lógica del servidor, API REST (FastAPI), modelos Pydantic, conexión a bases de datos SQLite y Qdrant, y procesamiento RAG/LLM.
2.  `/frontend`: Interfaz de usuario (Astro SSR híbrido + React para componentes dinámicos de cliente), estilizada con TailwindCSS.

## 🛠 Instalación y Ejecución Local

Para ejecutar este proyecto en tu entorno de desarrollo, asegúrate de tener instalados **Node.js** y **Python 3.11+**. 

⚠️ **Requisito Previo de IA:** Debes tener instalado y ejecutándose **Ollama** si deseas probar la generación de queries optimizadas con IA de forma local. Asegúrate de tener descargado algún modelo, por ejemplo:
```bash
ollama run llama3.1:8b
```
*(Mantén Ollama corriendo en segundo plano antes de iniciar AgriSearch).*

### ▶️ Ejecución Rápida (Recomendado para Windows)
Hemos incluido un script inteligente en la raíz del proyecto para facilitar el arranque y **su primera ejecución**.

Simplemente haz doble clic en el archivo:
> `start_agrisearch.bat`

Al hacer esto por primera vez, el script se encargará automáticamente de:
- Verificar o instalar el entorno virtual en `backend/` usando `uv` (o recursando a `pip` tradicional si no tienes `uv` instalado).
- Descargar e instalar todas las dependencias de Python y Node (`npm install`).
- Crear las carpetas de datos locales para SQLite y Qdrant.
- Abrir las terminales independientes y lanzar el navegador.

---

### Instalación Manual Paso a Paso

#### 1. Configuración del Backend

1. Navega al directorio del backend:
   ```bash
   cd backend
   ```
2. Crea y activa un entorno virtual (se recomienda usar `uv` o `venv` puro):
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # En Windows
   ```
3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   # o utilizando uv: uv pip install -r requirements.txt
   ```
4. Inicia el servidor de desarrollo Uvicorn:
   ```bash
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

Además, en la carpeta `.agents/workflows/` encontrarás reglas definidas de comportamiento de commits y creación de nuevos endpoints/pantallas para la estandarización de código.

## 🧑‍💻 Autoría

Desarrollado y mantenido por **ALEX** (@alex).

## 📄 Licencia

Este proyecto se distribuye bajo la licencia **MIT**. Eres libre de usar, modificar y distribuir el código, manteniendo siempre el reconocimiento al autor original.
Licencia abierta con fines investigativos y educativos.
