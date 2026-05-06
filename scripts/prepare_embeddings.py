"""
Script pre-vuelo: Genera embeddings y popula datos_cribado.sqlite.

Lee articulos de agrisearch.db, genera embeddings con all-MiniLM-L6-v2,
y los almacena en una BD SQLite optimizada para el worker Rust de Active Learning.

Ejecutar:
    cd AgriSearch (raiz del proyecto)
    uv run python scripts/prepare_embeddings.py --project-id <UUID>

Opcional: exportar modelo a ONNX para inferencia desde Rust:
    uv run python scripts/prepare_embeddings.py --project-id <UUID> --export-onnx
"""
import argparse
import sqlite3
import struct
import sys
from pathlib import Path


def serialize_f32(vector: list[float]) -> bytes:
    """Serializa vector float32 para almacenamiento en SQLite (compatible con sqlite-vec)."""
    return struct.pack(f"{len(vector)}f", *vector)


def get_db_path() -> Path:
    """Busca agrisearch.db en ubicaciones comunes."""
    candidates = [
        Path("backend/data/agrisearch.db"),
        Path("backend/agrisearch.db"),
        Path("data/agrisearch.db"),
        Path("agrisearch.db"),
    ]
    for p in candidates:
        if p.exists():
            return p.resolve()
    return candidates[0]


def main(project_id: str, db_path: str | None = None, export_onnx: bool = False) -> None:
    src_db = Path(db_path) if db_path else get_db_path()

    if not src_db.exists():
        print(f"ERROR: Base de datos no encontrada en {src_db}")
        print("Ejecuta primero el backend para crear la BD o especifica --db-path")
        sys.exit(1)

    print(f"📂 Base de datos origen: {src_db}")

    # 1. Leer articulos del proyecto
    conn_src = sqlite3.connect(str(src_db))
    conn_src.row_factory = sqlite3.Row
    articles = conn_src.execute(
        """
        SELECT a.id, a.title, a.abstract, a.keywords
        FROM articles a
        JOIN search_queries sq ON a.search_query_id = sq.id
        WHERE sq.project_id = ?
          AND a.download_status = 'success'
        """,
        (project_id,),
    ).fetchall()
    conn_src.close()

    if not articles:
        print(f"⚠️  No se encontraron articulos con download_status='success' para el proyecto {project_id}")
        print("   Crea una busqueda y descarga PDFs primero, o usa --include-pending")
        sys.exit(1)

    print(f"📚 {len(articles)} articulos encontrados con PDF descargado")

    # 2. Cargar modelo y generar embeddings
    print("🔄 Cargando modelo all-MiniLM-L6-v2...")
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")

    texts = [
        f"{a['title']} {a['abstract'] or ''} {a['keywords'] or ''}".strip()
        for a in articles
    ]
    print("🧠 Generando embeddings (384 dimensiones, L2-normalizados)...")
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)

    # Validar normalizacion
    import numpy as np

    norms = np.linalg.norm(embeddings, axis=1)
    print(f"   Norma L2: min={norms.min():.4f}, max={norms.max():.4f}, mean={norms.mean():.4f}")

    # 3. Crear datos_cribado.sqlite
    out_path = Path("active_learning_worker/datos_cribado.sqlite")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Eliminar si existe para recrear limpio
    if out_path.exists():
        out_path.unlink()
        print(f"🗑️  Base de datos anterior eliminada: {out_path}")

    conn = sqlite3.connect(str(out_path))

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            abstract TEXT,
            keywords TEXT,
            status TEXT DEFAULT 'pending',
            priority_score REAL DEFAULT 0.0,
            suggestion_score REAL DEFAULT 0.0,
            uncertainty REAL DEFAULT 0.5
        );

        CREATE TABLE IF NOT EXISTS embeddings (
            article_id TEXT PRIMARY KEY,
            vector BLOB NOT NULL,
            FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);
        CREATE INDEX IF NOT EXISTS idx_articles_priority ON articles(priority_score DESC);
        """
    )

    # Insertar en transaccion unica para velocidad
    with conn:
        for i, article in enumerate(articles):
            conn.execute(
                "INSERT INTO articles (id, title, abstract, keywords) VALUES (?, ?, ?, ?)",
                (article["id"], article["title"], article["abstract"], article["keywords"]),
            )
            conn.execute(
                "INSERT INTO embeddings (article_id, vector) VALUES (?, ?)",
                (article["id"], serialize_f32(embeddings[i].tolist())),
            )

    conn.close()
    size_kb = out_path.stat().st_size / 1024
    print(f"✅ Base de datos creada: {out_path} ({size_kb:.0f} KB)")

    # 4. Exportar modelo a ONNX (opcional)
    if export_onnx:
        print("\n📦 Exportando modelo a ONNX...")
        from optimum.onnxruntime import ORTModelForFeatureExtraction
        from transformers import AutoTokenizer

        model_name = "sentence-transformers/all-MiniLM-L6-v2"
        onnx_dir = Path("active_learning_worker/models/minilm-onnx")
        onnx_dir.mkdir(parents=True, exist_ok=True)

        print("   Convirtiendo modelo (esto puede tardar unos minutos)...")
        ort_model = ORTModelForFeatureExtraction.from_pretrained(model_name, export=True)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        ort_model.save_pretrained(str(onnx_dir))
        tokenizer.save_pretrained(str(onnx_dir))

        model_size_mb = sum(f.stat().st_size for f in onnx_dir.rglob("*")) / (1024 * 1024)
        print(f"✅ Modelo ONNX exportado: {onnx_dir} ({model_size_mb:.1f} MB)")

    # 5. Resumen
    print("\n📊 Resumen:")
    print(f"   Articulos: {len(articles)}")
    print(f"   Dimensiones embedding: {embeddings.shape[1]}")
    print(f"   Base de datos: {out_path} ({size_kb:.0f} KB)")
    if export_onnx:
        print(f"   Modelo ONNX: {onnx_dir}")
    print("\n🚀 Siguiente paso: compilar y ejecutar el worker Rust")
    print("   cd active_learning_worker && cargo run --release")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Genera embeddings para Active Learning Worker (Rust)"
    )
    parser.add_argument(
        "--project-id",
        required=True,
        help="UUID del proyecto en AgriSearch",
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="Ruta a agrisearch.db (default: busca en backend/, data/, raiz)",
    )
    parser.add_argument(
        "--export-onnx",
        action="store_true",
        help="Exportar modelo a formato ONNX para inferencia desde Rust",
    )
    args = parser.parse_args()
    main(args.project_id, args.db_path, args.export_onnx)
