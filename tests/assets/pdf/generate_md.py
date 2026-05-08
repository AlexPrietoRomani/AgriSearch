"""
Archivo: generate_md.py
Modificación: 2026-05-08
Autor: Alex Prieto

Descripción:
Script de utilidad temporal para generar el contenido Markdown de los nuevos 
artículos descargados desde ArXiv. Facilita la expansión del README de activos 
manteniendo el formato de metadatos requerido.

Nota: Este es un script de un solo uso para mantenimiento de activos.
"""

import json

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

output_md = ""
list_idx = 9
for p in papers:
    pid = p['id']
    if pid in selected_ids:
        title = p['title'].replace('\n', ' ')
        doi_id = pid.split('v')[0]
        output_md += f"### {list_idx}. {title[:50]}... — `{pid}`\n"
        output_md += f"- **Título:** {title}\n"
        output_md += f"- **Tema:** Deep learning applied to agriculture\n"
        output_md += f"- **Variables espectrales:** Multispectral/RGB\n"
        output_md += f"- **Uso esperado:** Expand dataset\n"
        output_md += f"- **Resultado esperado:** Agriculture, Deep Learning\n"
        output_md += f"- **DOI:** 10.48550/arXiv.{doi_id}\n\n"
        list_idx += 1

with open('generated_readme_append.md', 'w', encoding='utf-8') as f:
    f.write(output_md)
