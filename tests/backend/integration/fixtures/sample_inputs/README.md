# Fixtures de Prueba — Archivos de Entrada

Coloca aquí archivos de prueba reales para los tests de integración del pipeline de parsing.

## Estructura esperada

```
sample_inputs/
├── scientific_article.pdf     # PDF de artículo científico (doble columna, tablas, figuras)
├── simple_report.pdf          # PDF simple (una columna, sin layout complejo)
├── sample_document.docx       # Documento Word de prueba
├── sample_spreadsheet.xlsx    # Hoja de cálculo de prueba
└── sample_presentation.pptx   # Presentación de prueba
```

> ⚠️ **No subir archivos grandes al repositorio.** Usa PDFs de ≤5 páginas para tests rápidos.
> Los archivos `.pdf`, `.docx`, `.xlsx`, `.pptx` están en el `.gitignore` global.
> Si necesitas persistirlos, usa Git LFS o agrega excepciones explícitas.
