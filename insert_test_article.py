import sqlite3
import uuid
from datetime import datetime

DB_PATH = "agrisearch.db"
PROJECT_ID = "75e9f074-593d-4c64-a9f8-71691ae1bb70"
ARTICLE_ID = str(uuid.uuid4())
# Important: local_pdf_path should be relative if possible or precisely match the app logic.
# The app logic in pdf_enrichment_service scan_and_match_pdfs returns the path as found by glob.
# When downloading, I put it in "backend/data/projects/.../pdfs/Alreshidi_2019.pdf" 
# Relative to ROOT: "backend/data/projects/..."
# Relative to BACKEND: "data/projects/..."
# Uvicorn started at ROOT. settings.base_data_dir = "data/projects"
# So PDF should be in "data/projects/..." at root.

PDF_PATH = rf"C:\Users\ALEX\Github\AgriSearch\data\projects\{PROJECT_ID}\pdfs\Alreshidi_2019.pdf"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Insert the article
cursor.execute('''
    INSERT INTO articles (
        id, project_id, doi, title, authors, year, abstract, journal, url, 
        local_pdf_path, download_status, is_duplicate, source_database, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (
    ARTICLE_ID,
    PROJECT_ID,
    "10.48550/arXiv.1906.03106",
    "Smart Sustainable Agriculture (SSA) Solution Underpinned by Internet of Things (IoT) and Artificial Intelligence (AI)",
    "Eissa Alreshidi",
    2019,
    "The Internet of Things (IoT) and Artificial Intelligence (AI) have been employed in agriculture over a long period of time...",
    "arXiv",
    "https://arxiv.org/pdf/1906.03106v1",
    PDF_PATH,
    "success",
    False,
    "arXiv",
    datetime.now().isoformat(),
    datetime.now().isoformat()
))

conn.commit()
conn.close()
print(f"Article inserted with ID: {ARTICLE_ID}")
