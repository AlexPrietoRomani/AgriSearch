"""
Crea una base de datos de prueba para el benchmark del Active Learning Worker.

Genera 100 articulos sinteticos con embeddings aleatorios de 384 dimensiones
en datos_cribado.sqlite.

Ejecutar:
    cd active_learning_worker
    python ../scripts/create_test_db.py
"""
import sqlite3
import struct
import random
import math

DB_PATH = "active_learning_worker/datos_cribado.sqlite"
NUM_ARTICLES = 100
EMBEDDING_DIM = 384


def random_embedding(is_accepted: bool) -> bytes:
    """Genera un embedding aleatorio con sesgo segun la clase."""
    vec = []
    for i in range(EMBEDDING_DIM):
        base = 0.3 if is_accepted else -0.3
        val = base + random.gauss(0, 0.5)
        vec.append(val)

    # Normalizar L2
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]

    return struct.pack(f"{EMBEDDING_DIM}f", *vec)


def main():
    print(f"Creando base de datos de prueba: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode = WAL;")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            abstract TEXT,
            keywords TEXT,
            status TEXT DEFAULT 'pending',
            priority_score REAL DEFAULT 0.0,
            suggestion_score REAL DEFAULT 0.0,
            uncertainty REAL DEFAULT 0.0
        );
        CREATE TABLE IF NOT EXISTS embeddings (
            article_id TEXT PRIMARY KEY,
            vector BLOB,
            FOREIGN KEY (article_id) REFERENCES articles(id)
        );
    """)

    topics_accepted = [
        ("crop yield", "wheat, maize, rice", "Agricultural productivity in cereal crops"),
        ("irrigation", "water, drip, efficiency", "Water management in arid regions"),
        ("soil health", "organic matter, nutrients", "Soil carbon sequestration methods"),
        ("pest control", "IPM, biological control", "Integrated pest management strategies"),
        ("sustainable farming", "agroecology, organic", "Sustainable agricultural practices"),
    ]

    topics_rejected = [
        ("economics", "finance, market, trade", "Agricultural economics and policy"),
        ("history", "historical, ancient", "History of agricultural practices"),
        ("sociology", "rural, community", "Social aspects of farming communities"),
        ("legislation", "law, regulation, policy", "Agricultural legislation review"),
        ("philosophy", "ethics, moral", "Philosophical aspects of food systems"),
    ]

    random.seed(42)

    for i in range(NUM_ARTICLES):
        article_id = f"test-article-{i:04d}"

        if i < 20:
            # First 20: 10 accepted, 10 rejected (labeled for ML)
            if i < 10:
                topic, keywords, abstract = topics_accepted[i % len(topics_accepted)]
                status = "accepted"
                is_accepted = True
            else:
                topic, keywords, abstract = topics_rejected[i % len(topics_rejected)]
                status = "rejected"
                is_accepted = False
        else:
            # Remaining 80: pending
            if random.random() < 0.5:
                topic, keywords, abstract = topics_accepted[i % len(topics_accepted)]
            else:
                topic, keywords, abstract = topics_rejected[i % len(topics_rejected)]
            status = "pending"
            is_accepted = False

        title = f"Study on {topic.title()} — Article {i}"
        priority = random.uniform(0, 1) if status == "pending" else 0.0

        conn.execute(
            "INSERT INTO articles (id, title, abstract, keywords, status, priority_score) VALUES (?, ?, ?, ?, ?, ?)",
            (article_id, title, abstract, keywords, status, priority),
        )

        embedding = random_embedding(is_accepted)
        conn.execute(
            "INSERT INTO embeddings (article_id, vector) VALUES (?, ?)",
            (article_id, embedding),
        )

    conn.commit()

    # Verify
    total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM articles WHERE status = 'pending'").fetchone()[0]
    accepted = conn.execute("SELECT COUNT(*) FROM articles WHERE status = 'accepted'").fetchone()[0]
    rejected = conn.execute("SELECT COUNT(*) FROM articles WHERE status = 'rejected'").fetchone()[0]
    embeddings = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]

    conn.close()

    print(f"  Total articulos: {total}")
    print(f"  Accepted: {accepted}")
    print(f"  Rejected: {rejected}")
    print(f"  Pending: {pending}")
    print(f"  Embeddings: {embeddings}")
    print(f"  DB size: {__import__('os').path.getsize(DB_PATH) / 1024:.0f} KB")
    print("  Listo para benchmark!")


if __name__ == "__main__":
    main()
