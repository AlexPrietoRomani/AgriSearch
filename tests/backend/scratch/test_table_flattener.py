import sys
import os
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.append(str(backend_path))

from app.services.document_parser_service import TableFlattener

# Tabla de ejemplo en formato MarkItDown
test_md = """
## Resultados

| Cultivo | Rendimiento (t/ha) | Tratamiento |
|---------|-------------------|-------------|
| Trigo   | 4.2               | Control     |
| Maíz    | 8.7               | Fertilizado |
| Soja    | 3.1               | Inoculado   |

Texto después de la tabla.
"""

meta = {"title": "Evaluación de cultivos", "authors": "García J., López M.", "year": 2024}
result = TableFlattener.flatten(test_md, meta)
print("--- OUTPUT ---")
print(result)
print("--- END ---")
