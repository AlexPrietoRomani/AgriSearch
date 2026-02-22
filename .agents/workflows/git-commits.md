---
description: Convenciones para mensajes de commit en Git (Español)
---

# Convenciones de Commits para AgriSearch

Para mantener el historial del proyecto limpio y comprensible, todos los mensajes de commit deben seguir la especificación de **Conventional Commits**, pero con las descripciones en **español**.

## Estructura del Mensaje

El mensaje debe tener la siguiente estructura:

```
<tipo>[ámbito opcional]: <descripción>

[cuerpo opcional]

[pie opcional]
```

## Tipos Permitidos (Mantenemos los prefijos estándar en inglés)

*   **feat**: Una nueva característica o funcionalidad.
*   **fix**: Corrección de un error (bug).
*   **docs**: Cambios únicamente en la documentación (ej. README.md, plan_a_seguir.md).
*   **style**: Cambios que no afectan el significado del código (espacios en blanco, formato, punto y coma faltante, etc.).
*   **refactor**: Un cambio en el código que ni corrige un error ni añade una característica (reestructuración, optimización).
*   **perf**: Un cambio en el código que mejora el rendimiento.
*   **test**: Añadir pruebas faltantes o corregir pruebas existentes.
*   **build**: Cambios que afectan el sistema de compilación o dependencias externas (ej. npm, pip, astro).
*   **ci**: Cambios en los archivos y scripts de configuración de CI (ej. GitHub Actions).
*   **chore**: Tareas de mantenimiento, actualización de dependencias, etc. que no modifican el código fuente ni las pruebas.
*   **revert**: Revierte un commit anterior.

## Reglas Obligatorias

1.  **Idioma**: Obligatoriamente la `<descripción>`, el `[cuerpo]` y el `[pie]` deben estar en **Español**.
2.  **Longitud de la descripción**: No debe superar los 50 caracteres (idealmente).
3.  **Mayúsculas y puntuación**: La descripción NO debe empezar con mayúscula (a menos que sea un nombre propio) y NO debe terminar con un punto.
4.  **Verbo imperativo**: Usa el modo imperativo en tiempo presente ("añade" no "añadido" ni "añadió"). Ejemplo: `feat: añade botón de descarga de PDF`.

## Ejemplos de uso

**Bien:**
- `feat: añade soporte para búsqueda con YOLO en ArXiv`
- `fix(backend): resuelve bloqueo de base de datos SQLite en Windows`
- `docs: actualiza el README con instrucciones detalladas`
- `refactor(frontend): reorganiza los componentes del SearchWizard`
- `build: actualiza dependencias de React a la última versión`

**Mal:**
- `Added new feature for YOLO` (Inglés)
- `feat: Añadido botón de descarga.` (Empieza con mayúscula, termina en punto y usa pasado)
- `fix: corrección de errores en la db` (No especifica qué se corrigió)

Al realizar cualquier commit en este repositorio, asegúrate de aplicar estas reglas.
