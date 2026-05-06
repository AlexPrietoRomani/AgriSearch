/// Capa de acceso a datos para el Active Learning Worker.
///
/// Abstrae operaciones CRUD sobre `datos_cribado.sqlite`, incluyendo
/// lectura de articulos, persistencia de decisiones, extraccion de
/// embeddings para ML y actualizacion de prioridades.
use anyhow::{Context, Result};
use ndarray::{Array1, Array2};
use rusqlite::{params, Connection, OpenFlags};
use std::path::Path;
use std::sync::Arc;
use tokio::sync::Mutex;

/// Representa un articulo para el flujo de screening.
#[derive(Debug, Clone)]
pub struct Article {
    pub id: String,
    pub title: String,
    pub r#abstract: Option<String>,
    pub keywords: Option<String>,
    pub status: String,
    pub priority_score: f64,
    pub suggestion_score: f64,
    pub uncertainty: f64,
}

/// Estado de una decision de screening.
#[derive(Debug, Clone, PartialEq)]
pub enum DecisionStatus {
    Accepted,
    Rejected,
    Maybe,
}

impl DecisionStatus {
    pub fn as_str(&self) -> &str {
        match self {
            DecisionStatus::Accepted => "accepted",
            DecisionStatus::Rejected => "rejected",
            DecisionStatus::Maybe => "maybe",
        }
    }

    pub fn from_str(s: &str) -> Self {
        match s {
            "accepted" | "include" => DecisionStatus::Accepted,
            "rejected" | "exclude" => DecisionStatus::Rejected,
            _ => DecisionStatus::Maybe,
        }
    }
}

/// Wrapper thread-safe y Cloneable para la conexion SQLite.
#[derive(Clone)]
pub struct DbPool {
    pub conn: Arc<Mutex<Connection>>,
}

impl DbPool {
    /// Abre o crea la base de datos en la ruta especificada.
    pub fn open(path: impl AsRef<Path>) -> Result<Self> {
        let conn = Connection::open_with_flags(
            path,
            OpenFlags::SQLITE_OPEN_READ_WRITE | OpenFlags::SQLITE_OPEN_CREATE,
        )
        .context("Failed to open SQLite database")?;

        // Optimizaciones para baja latencia
        conn.execute_batch(
            "
            PRAGMA journal_mode = WAL;
            PRAGMA synchronous = NORMAL;
            PRAGMA cache_size = -64000;
            PRAGMA temp_store = MEMORY;
            ",
        )
        .context("Failed to set PRAGMAs")?;

        Ok(DbPool {
            conn: Arc::new(Mutex::new(conn)),
        })
    }

    /// Lee el siguiente articulo pendiente con mayor priority_score.
    pub async fn get_next_article(&self) -> Result<Option<Article>> {
        let conn = self.conn.lock().await;
        let mut stmt = conn.prepare(
            "SELECT id, title, abstract, keywords, status,
                    priority_score, suggestion_score, uncertainty
             FROM articles
             WHERE status = 'pending'
             ORDER BY priority_score DESC
             LIMIT 1",
        )?;

        let article = stmt.query_row([], |row| {
            Ok(Article {
                id: row.get(0)?,
                title: row.get(1)?,
                r#abstract: row.get(2)?,
                keywords: row.get(3)?,
                status: row.get(4)?,
                priority_score: row.get(5)?,
                suggestion_score: row.get(6)?,
                uncertainty: row.get(7)?,
            })
        });

        match article {
            Ok(a) => Ok(Some(a)),
            Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
            Err(e) => Err(e.into()),
        }
    }

    /// Actualiza la decision de un articulo.
    pub async fn update_decision(&self, id: &str, status: &DecisionStatus) -> Result<()> {
        let conn = self.conn.lock().await;
        conn.execute(
            "UPDATE articles SET status = ?1 WHERE id = ?2",
            params![status.as_str(), id],
        )?;
        Ok(())
    }

    /// Obtiene embeddings de articulos ya etiquetados (accepted/rejected).
    /// Retorna (matriz de vectores, vector de labels donde 1=accepted, 0=rejected).
    pub async fn get_labeled_embeddings(&self) -> Result<(Array2<f32>, Array1<i32>)> {
        let conn = self.conn.lock().await;

        let mut stmt = conn.prepare(
            "SELECT e.vector, a.status
             FROM embeddings e
             JOIN articles a ON e.article_id = a.id
             WHERE a.status IN ('accepted', 'rejected')",
        )?;

        let rows = stmt.query_map([], |row| {
            let blob: Vec<u8> = row.get(0)?;
            let status: String = row.get(1)?;
            Ok((blob, status))
        })?;

        let mut vectors: Vec<Vec<f32>> = Vec::new();
        let mut labels: Vec<i32> = Vec::new();

        for row in rows {
            let (blob, status) = row?;
            let dims = blob.len() / 4;
            let mut vec_f32 = vec![0.0f32; dims];
            for i in 0..dims {
                let bytes = [blob[i * 4], blob[i * 4 + 1], blob[i * 4 + 2], blob[i * 4 + 3]];
                vec_f32[i] = f32::from_ne_bytes(bytes);
            }
            vectors.push(vec_f32);
            labels.push(if status == "accepted" { 1 } else { 0 });
        }

        if vectors.is_empty() {
            return Ok((Array2::zeros((0, 384)), Array1::zeros(0)));
        }

        let n = vectors.len();
        let d = vectors[0].len();
        let mut matrix = Array2::zeros((n, d));
        for (i, v) in vectors.iter().enumerate() {
            for (j, &val) in v.iter().enumerate() {
                matrix[[i, j]] = val;
            }
        }

        Ok((matrix, Array1::from(labels)))
    }

    /// Obtiene embeddings de articulos pendientes.
    /// Retorna (lista de IDs, matriz de vectores).
    pub async fn get_pending_embeddings(&self) -> Result<(Vec<String>, Array2<f32>)> {
        let conn = self.conn.lock().await;

        let mut stmt = conn.prepare(
            "SELECT e.vector, a.id
             FROM embeddings e
             JOIN articles a ON e.article_id = a.id
             WHERE a.status = 'pending'",
        )?;

        let rows = stmt.query_map([], |row| {
            let blob: Vec<u8> = row.get(0)?;
            let id: String = row.get(1)?;
            Ok((blob, id))
        })?;

        let mut vectors: Vec<Vec<f32>> = Vec::new();
        let mut ids: Vec<String> = Vec::new();

        for row in rows {
            let (blob, id) = row?;
            let dims = blob.len() / 4;
            let mut vec_f32 = vec![0.0f32; dims];
            for i in 0..dims {
                let bytes = [blob[i * 4], blob[i * 4 + 1], blob[i * 4 + 2], blob[i * 4 + 3]];
                vec_f32[i] = f32::from_ne_bytes(bytes);
            }
            vectors.push(vec_f32);
            ids.push(id);
        }

        if vectors.is_empty() {
            return Ok((ids, Array2::zeros((0, 384))));
        }

        let n = vectors.len();
        let d = vectors[0].len();
        let mut matrix = Array2::zeros((n, d));
        for (i, v) in vectors.iter().enumerate() {
            for (j, &val) in v.iter().enumerate() {
                matrix[[i, j]] = val;
            }
        }

        Ok((ids, matrix))
    }

    /// Actualiza las prioridades de articulos pendientes en una transaccion atomica.
    pub async fn update_priorities(&self, rankings: &[(String, f64, f64, f64)]) -> Result<()> {
        let conn = self.conn.lock().await;
        let tx = conn.unchecked_transaction()?;

        {
            let mut stmt = tx.prepare(
                "UPDATE articles
                 SET priority_score = ?1,
                     suggestion_score = ?2,
                     uncertainty = ?3
                 WHERE id = ?4",
            )?;

            for (id, priority, suggestion, uncertainty) in rankings {
                stmt.execute(params![priority, suggestion, uncertainty, id])?;
            }
        }

        tx.commit()?;
        Ok(())
    }

    /// Retorna contadores de articulos por estado.
    pub async fn get_stats(&self) -> Result<Stats> {
        let conn = self.conn.lock().await;

        let pending: i64 = conn.query_row(
            "SELECT COUNT(*) FROM articles WHERE status = 'pending'",
            [],
            |r| r.get(0),
        )?;

        let accepted: i64 = conn.query_row(
            "SELECT COUNT(*) FROM articles WHERE status = 'accepted'",
            [],
            |r| r.get(0),
        )?;

        let rejected: i64 = conn.query_row(
            "SELECT COUNT(*) FROM articles WHERE status = 'rejected'",
            [],
            |r| r.get(0),
        )?;

        let maybe: i64 = conn.query_row(
            "SELECT COUNT(*) FROM articles WHERE status = 'maybe'",
            [],
            |r| r.get(0),
        )?;

        let total = pending + accepted + rejected + maybe;

        Ok(Stats {
            total,
            pending,
            accepted,
            rejected,
            maybe,
        })
    }

    /// Cuenta el total de decisiones tomadas.
    pub async fn get_decision_count(&self) -> Result<i64> {
        let conn = self.conn.lock().await;
        let count: i64 = conn.query_row(
            "SELECT COUNT(*) FROM articles WHERE status != 'pending'",
            [],
            |r| r.get(0),
        )?;
        Ok(count)
    }
}

/// Estadisticas del pool de articulos.
#[derive(Debug, Clone)]
pub struct Stats {
    pub total: i64,
    pub pending: i64,
    pub accepted: i64,
    pub rejected: i64,
    pub maybe: i64,
}
