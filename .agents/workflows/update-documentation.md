---
description: Como registrar cambios en la documentación del proyecto
---

# Workflow: Actualizar Documentación Técnica

Siempre que se añada una nueva funcionalidad significativa, se resuelva un bug crítico, o se incluya un nuevo flujo de información en la aplicación AgriSearch, debes documentar obligatoriamente dicho cambio.

## Archivos a Actualizar

Para asegurar la trazabilidad del código y sus dependencias, es OBLIGATORIO mantener estos archivos sincronizados después de cualquier tarea completada (o como parte de los Commits finales de una iteración):

1. **`docs/documentation.md`**: (Obligatorio en todo cambio). Debe incluir explicaciones funcionales, algoritmos, y reglas de negocio añadidas.
2. **`docs/arquitectura.md`**: (Obligatorio en cambios que toquen archivos o flujos). Si modificaste cómo se comunican el frontend y el backend, o interviniste modelos MVC, actualiza los diagramas Mermaid correspondientes referenciando los nuevos puertos o métodos.
3. **`docs/plan_a_seguir.md`**: (Obligatorio SOLO en cambios MACRO o hitos). Modificar solo si completaste una gran fase (como implementar el Screening o desplegar la versión final).

## Pasos

1. Abre y lee los documentos usando la herramienta `view_file`.
2. Edita las secciones utilizando la herramienta de reemplazo de texto (`replace_file_content`).
3. Asegúrate de incluir:
   - Nombre de la funcionalidad o solución.
   - Componentes frontend (archivos `tsx`, `astro`) y endpoints backend modificados.
   - Cualquier dependencia, modelo de base de datos o comando externo necesario para su correcto despliegue.
4. **Regla de Idioma Obligatoria:** Toda la documentación (docstrings tipo `""" """`) y comentarios de línea (`#` o `//`) deben escribirse en **Español**, al igual que los `.md`. Sin embargo, los nombres de variables, funciones, parámetros y schemas de la base de código siempre se mantendrán en **Inglés** por convención técnica.
5. Incorpóralo a tu commit en caso de ser necesario (`git add docs/ .agents/ ...`).
