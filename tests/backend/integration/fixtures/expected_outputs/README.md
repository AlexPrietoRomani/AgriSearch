# Outputs Esperados — Archivos de Referencia

Contiene los Markdown de referencia generados por cada parser para validar la calidad de la extracción.

## Estructura esperada

```
expected_outputs/
├── scientific_article_opendataloader.md   # Output de OpenDataLoader PDF para el artículo científico
├── scientific_article_markitdown.md       # Output de MarkItDown para el mismo PDF (comparación)
├── simple_report_markitdown.md            # Output de MarkItDown para PDF simple
├── sample_document_markitdown.md          # Output de MarkItDown para DOCX
└── sample_spreadsheet_markitdown.md       # Output de MarkItDown para XLSX
```

## Criterios de calidad para los outputs

- [ ] Contiene front-matter YAML válido (`---` al inicio y al final)
- [ ] Campo `parser_engine` presente (`opendataloader` o `markitdown`)
- [ ] Tablas aplanadas por TableFlattener (no deben quedar `|` de tablas markdown)
- [ ] Headings preservados (`##`, `###`)
- [ ] Longitud mínima: ≥1000 caracteres para artículos científicos
