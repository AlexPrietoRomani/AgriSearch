---
description: Como registrar cambios en documentation.md
---

# Workflow: Actualizar Documentación Técnica

Siempre que se añada una nueva funcionalidad significativa, se resuelva un bug crítico, o se incluya un nuevo flujo de información en la aplicación AgriSearch, debes (como asistente) registrar dicho cambio en el archivo `documentation.md` alojado en la raíz del proyecto.

## Pasos

1. Abre y lee el archivo `documentation.md` usando la herramienta `view_file`.
2. Identifica la sección correspondiente (ej. **Registro de Cambios y Funcionalidades**, **Bugs y Errores Conocidos**, o **Dependencias Críticas**). Si no existe, créala.
3. Edita la sección utilizando la herramienta de reemplazo de texto o usando bloques completos con descripciones concisas.
4. Asegúrate de incluir:
   - Nombre de la funcionalidad o solución.
   - Componentes frontend (archivos `tsx`, `astro`) y endpoints backend modificados.
   - Cualquier dependencia, modelo de base de datos o comando externo necesario para su correcto despliegue.
5. **Regla de Idioma Obligatoria:** Toda la documentación (docstrings tipo `""" """`) y comentarios de línea (`#` o `//`) deben escribirse en **Español**, tal como es el proyecto general. Sin embargo, los nombres de variables, funciones, parámetros y schemas de la base de código deben mantenerse en **Inglés** por convención técnica. (Ej: `def analyze_data(): # Analiza los datos de la base`).
6. Incorpóralo a tu commit en caso de ser necesario.
