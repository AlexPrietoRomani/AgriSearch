"""
Archivo: update_readme.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Script de automatización para inyectar nuevos registros de artículos, comandos 
de descarga y estados de archivos en el README.md de activos. Realiza reemplazos 
de texto basados en patrones para asegurar que la tabla de estado esté siempre 
actualizada.

Nota: Este es un script de un solo uso para mantenimiento de activos.
"""

import json
import re

with open('C:/Users/ALEX/.gemini/antigravity/brain/0fa32aeb-9d0b-4d98-8e1d-9a2e2a6da1eb/.system_generated/steps/80/output.txt', 'r', encoding='utf-8') as f:
    data = json.load(f)

papers = data['papers']
selected_ids = [
    '1807.11809v1', '2403.09554v2', '1809.03322v1', '2308.08611v1',
    '2004.14421v1', '2505.07840v1', '2305.10084v1', '2308.07231v3',
    '2602.17683v2', '2505.18206v1', '2312.09730v1', '2404.08931v1',
    '2111.13663v1', '2303.02632v2', '2304.13880v1', '2210.01272v3',
    '2110.12638v1', '2201.02885v2', '2101.10861v4', '2603.01932v2'
]

# Create the new paper entries
new_entries = "\n"
list_idx = 9
for p in papers:
    pid = p['id']
    if pid in selected_ids:
        title = p['title'].replace('\n', ' ')
        doi_id = pid.split('v')[0]
        new_entries += f"### {list_idx}. {title[:50]}... — `{pid}`\n"
        new_entries += f"- **Título:** {title}\n"
        new_entries += f"- **Tema:** Deep learning applied to agriculture\n"
        new_entries += f"- **Variables espectrales:** Multispectral/RGB\n"
        new_entries += f"- **Uso esperado:** Expand dataset\n"
        new_entries += f"- **Resultado esperado:** Agriculture, Deep Learning\n"
        new_entries += f"- **DOI:** 10.48550/arXiv.{doi_id}\n\n"
        list_idx += 1

with open('README.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Insert new entries before ## Descarga
content = content.replace("## Descarga", new_entries + "## Descarga")

# Insert new download commands
new_cmds = "\n".join([f"arxiv-mcp-server_download_paper --paper_id {pid}" for pid in selected_ids])
content = content.replace("```\n\nO descargar manualmente", f"{new_cmds}\n```\n\nO descargar manualmente")

# Insert new manual download links
new_links = "\n".join([f"- https://arxiv.org/pdf/{pid} (DOI: 10.48550/arXiv.{pid.split('v')[0]})" for pid in selected_ids])
content = content.replace("## Estado de Archivos", f"{new_links}\n\n## Estado de Archivos")

# Insert new status table rows
new_status = "\n".join([f"| `{pid}` | `{pid}.pdf` | ✅ Descargado |" for pid in selected_ids])
# also mark 2503.08348v1 and 2311.00429v2 as downloaded
content = content.replace("| `2503.08348v1` | `2503.08348v1.pdf` | ❌ Pendiente |", "| `2503.08348v1` | `2503.08348v1.pdf` | ✅ Descargado |")
content = content.replace("| `2311.00429v2` | `2311.00429v2.pdf` | ❌ Pendiente |", "| `2311.00429v2` | `2311.00429v2.pdf` | ✅ Descargado |")
content = content.replace("## Notas", f"{new_status}\n\n## Notas")

with open('README.md', 'w', encoding='utf-8') as f:
    f.write(content)
