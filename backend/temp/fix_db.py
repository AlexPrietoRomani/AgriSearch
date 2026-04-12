import sqlite3
import re
from pathlib import Path
import unicodedata

def sanitize(name):
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8')
    name = re.sub(r'[^\w\s-]', '', name)
    return re.sub(r'[\s-]+', '_', name.strip())

conn = sqlite3.connect('../agrisearch.db')
c = conn.cursor()

c.execute('SELECT id, name FROM projects')
projects = {r[0]: r[1] for r in c.fetchall()}
total_fixed = 0

for p_id, p_name in projects.items():
    c.execute('SELECT id FROM search_queries WHERE project_id = ? ORDER BY created_at ASC', (p_id,))
    sq_map = {r[0]: f'Busqueda_{idx}' for idx, r in enumerate(c.fetchall(), 1)}
    
    c.execute('SELECT id, authors, year, title, search_query_id FROM articles WHERE project_id = ? AND download_status = "SUCCESS" AND local_pdf_path IS NULL', (p_id,))
    articles = c.fetchall()
    
    fixed = 0
    for art in articles:
        a_id, authors, year, title, sq_id = art
        sname = sq_map.get(sq_id, 'Sin_Busqueda')
        base_dir = Path('data/projects') / sanitize(p_name) / sanitize(sname) / 'descargas'
        
        first_author = (authors or 'unknown').split(',')[0].strip().split()[-1]
        yr = str(year) if year else 'nd'
        
        tslug = re.sub(r'[<>:"/\\|?*]', '_', title)
        tslug = re.sub(r'\s+', '_', tslug)[:50]
        fname = f'{yr}_{first_author}_{tslug}.pdf'
        fpath = str(base_dir / fname).replace('\\\\', '/')
        
        c.execute('UPDATE articles SET local_pdf_path = ? WHERE id = ?', (fpath, a_id))
        fixed += 1
        total_fixed += 1
        
    if fixed > 0:
        print(f'Fixed {fixed} articles for project {p_name}')

conn.commit()
conn.close()
print(f'Done. Total fixed: {total_fixed}')
