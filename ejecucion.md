# Guía de Ejecución de AgriSearch 🚀

Este documento detalla paso a paso cómo preparar tu entorno y arrancar AgriSearch. Se divide en dos partes fundamentales: **Tu primera ejecución** (cuando acabas de descargar el proyecto) y **Ejecuciones recurrentes** (cuando el proyecto ya está instalado en tu equipo).

---

## Parte 1: Primera Ejecución (Instalación desde cero)

Si acabas de clonar el repositorio o es la primera vez que vas a arrancar AgriSearch, debes seguir estos pasos para asegurarte de que todas las herramientas y bases de datos están listas.

### 1. Requisitos Previos (Programas a instalar)
Asegúrate de tener instalados los siguientes programas en tu computadora:
- **Python 3.11+** (No olvides marcar la opción "Add Python to PATH" durante la instalación).
- **Node.js** (Versión LTS, típicamente la 20.x o superior).
- **Ollama**: Descárgalo desde [ollama.com](https://ollama.com/) e instálalo.

### 2. Configurar Ollama (Motores de IA)
AgriSearch requiere dos modelos locales de IA para funcionar correctamente: uno para la generación de búsquedas (Aya) y otro para entender y recuperar documentos abstractos matemáticamente (Nomic). 

Abre una consola (CMD o PowerShell) y ejecuta estos comandos uno por uno (Ollama descargará los modelos progresivamente):
```bash
# 1. Descargando el modelo ligero para Generar Consultas:
ollama pull aya:8b

# 2. Descargando el modelo de inmersión vectorial (Embeddings):
ollama pull nomic-embed-text
```

### 3. Configurar tus Accesos (Credenciales de API)
Varias bases de datos científicas integradas (como **CORE** y **Redalyc**) exigen permisos gratuitos para proveer resultados. 
1. Ve a la carpeta `backend` en el proyecto.
2. Haz una copia del archivo `.env.example` y renómbralo a `.env`.
3. Ábrelo con cualquier editor de texto. Adentro verás enlaces para registrarte gratuitamente en CORE, Redalyc y otras bases. Rellena los tokens generados tras los signos de igual (`=`). 
> **Nota:** Si omites este paso, al buscar con CORE o Redalyc activados obtendrás siempre 0 resultados.

### 4. Lanzar AgriSearch
Desde la raíz principal del proyecto, debes instalar las dependencias de ambas carpetas (`backend` y `frontend`). Puedes hacerlo automáticamente haciendo **doble clic** en:

📄 `start_agrisearch.cmd`

> **¿El doble clic no funciona o la ventana se cierra instantáneamente?**
> Abre una terminal genérica (CMD o PowerShell) dentro de la carpeta del proyecto y ejecuta estos comandos manualmente en **dos ventanas separadas**:
> 
> **Ventana 1 (Backend):** 
> ```bash
> cd backend
> python -m venv venv
> venv\Scripts\activate
> pip install -r requirements.txt
> uvicorn app.main:app --port 8000
> ```
> 
> **Ventana 2 (Frontend):**
> ```bash
> cd frontend
> npm install
> npm run dev
> ```
> Finalmente, abre en tu navegador web la dirección `http://localhost:4321`.

---

## Parte 2: Ejecuciones Recurrentes (Día a Día)

Si ya hiciste el **Paso 1** anteriormente, tu vida a partir de ahora es mucho más sencilla, no necesitas instalar nada más.

### 1. Arrancar la Inteligencia Artificial (Ollama)
Siempre debes cerciorarte de que el motor Ollama esté "encendido" en segundo plano antes de abrir la aplicación. 
Simplemente busca **Ollama** en el menú de inicio de Windows y dale clic (verás que aparece un icono con forma de llama pequeña en tu barra de tareas, cerca del reloj de Windows).
*Si prefieres hacerlo por consola:*
```bash
ollama serve
```

### 2. Arrancar la Aplicación
Con el Ollama encendido, simplemente ve a la carpeta de tu proyecto y haz **doble clic** en:

📄 `start_agrisearch.cmd`

El CMD levantará el servidor backend y el visor frontend automáticamente, y en un par de segundos se abrirá tu navegador predeterminado en `http://localhost:4321`.

> **Si tienes problemas ejecutando el acceso rápido `.cmd`:**
> Simplemente abre dos ventanas de terminal en tu carpeta del proyecto:
> 1. En la primera, enciende el backend: `cd backend && venv\Scripts\activate && uvicorn app.main:app --port 8000`
> 2. En la segunda, el frontend: `cd frontend && npm run dev`

¡Y listo! Ya puedes continuar con tu Revisión Sistemática PRISMA de forma estructurada.
