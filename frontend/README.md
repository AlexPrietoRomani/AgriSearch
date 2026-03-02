# Chat Búsqueda Sistemática - Frontend

Este es el frontend de la herramienta de Búsqueda Sistemática, construido con **Astro**, **React**, y **Tailwind CSS**.

## 🚀 Estructura del Proyecto

El proyecto está diseñado para ser rápido, modular y con un estilo visual "dark glassmorphic" de alto nivel.

```text
/
├── public/              # Archivos estáticos
├── src/
│   ├── components/      # Componentes React interactivos (islands)
│   ├── layouts/         # Layouts de Astro (ej. base HTML, estilos globales)
│   ├── lib/             # Funciones de utilidad y llamadas a la API (api.ts)
│   └── pages/           # Rutas automáticas de Astro (ej. index.astro, search.astro, screening.astro)
└── tailwind.config.mjs  # Configuración de Tailwind CSS
```

## 🌟 Funcionalidades Principales

- **Dashboard Principal**: Gestión de Proyectos, listado de búsquedas y revisiones pasadas y control general del pipeline mediante `ProjectDashboard.tsx`.
- **Wizard de Búsqueda Sistemática**: Un componente Multi-Step poderoso (`SearchWizard`) dividido en 4 pasos (Descripción, Revisión de Query LLC, Búsqueda asíncrona concurrente, Resultados con LaTeX y descarga PDF local).
- **Control Inteligente de Inputs**: Preservación del Prompt Natural en paralelo a las queries crudas. Control visual del número de artículos *no encontrados/sin enlace* disponible para descarga.
- **Sistema de Revisiones (Screening) Multi-Persona**: Una interfaz estricta (tipo Rayyan) que permite gestionar artículos con su PDF local en pantalla dividida o mediante modal. Traducciones automáticas vía LLM locales (Aya, Qwen, LLaMA), atajos de teclado y conteos en vivo.
- **Botones de Purga de Sesión**: Posibilidad de eliminar búsquedas o revisiones. Al borrar una revisión se usa "Eliminación Segura", manteniendo los PDFs descargados intactos en sus rutas sanitizadas (`Project_Name/Search_Name/descargas`).

## 🧞 Comandos Locales

Ejecutables desde la raíz de `frontend/` en tu terminal:

| Comando                   | Acción                                           |
| :------------------------ | :----------------------------------------------- |
| `npm install`             | Instala dependencias                             |
| `npm run dev`             | Inicia el servidor de desarrollo (`localhost:4321`) |
| `npm run build`           | Compila el sitio listo para producción a `./dist/`|
| `npm run preview`         | Previsualiza el build de producción localmente   |

## 🤝 Tecnologías Destacadas
- **Astro**: Core framework, manejando enrutamiento y SSR liviano.
- **React**: Interacciones complejas del cliente (via `client:only="react"` o `client:load`).
- **KaTeX / react-latex-next**: Renderizado matemático in-browser de ecuaciones LaTeX en abstracts.
- **Tailwind CSS + Glassmorphism**: Utilidades de estilo para visuales limpias, futuristas y altamente accesibles.
