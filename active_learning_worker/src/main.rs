use active_learning_worker::api;
use active_learning_worker::db::DbPool;
use active_learning_worker::ml;
use active_learning_worker::{AppState, TrainingTrigger};
use axum::{routing::get, Router, Json};
use serde_json::json;
use tokio::sync::mpsc;
use tower_http::cors::{Any, CorsLayer};

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();

    let db_path = std::env::var("DB_PATH")
        .unwrap_or_else(|_| "active_learning_worker/datos_cribado.sqlite".to_string());

    let db = match DbPool::open(&db_path) {
        Ok(pool) => {
            tracing::info!("Base de datos abierta: {}", db_path);
            Some(pool)
        }
        Err(e) => {
            tracing::warn!("No se pudo abrir la BD (se ejecutara sin datos): {}", e);
            None
        }
    };

    // Canal mpsc para re-entrenamiento en background
    let (tx, mut rx) = mpsc::channel::<TrainingTrigger>(100);

    // Spawn worker de re-entrenamiento
    if let Some(db_pool) = db.clone() {
        tokio::spawn(async move {
            while let Some(trigger) = rx.recv().await {
                match trigger {
                    TrainingTrigger::Retrain(strategy) => {
                        let start = std::time::Instant::now();
                        match ml::retrain_and_rerank(&db_pool, strategy).await {
                            Ok(n) => {
                                tracing::info!(
                                    "Re-entrenamiento completado: {} articulos en {:.2}ms",
                                    n,
                                    start.elapsed().as_secs_f64() * 1000.0
                                );
                            }
                            Err(e) => {
                                tracing::error!("Error en re-entrenamiento: {}", e);
                            }
                        }
                    }
                }
            }
        });
        tracing::info!("Worker de re-entrenamiento iniciado (canal mpsc)");
    }

    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    let app_state = AppState { db, tx };

    let app = Router::new()
        .route("/health", get(health_check))
        .merge(api::router())
        .layer(cors)
        .with_state(app_state);

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3001")
        .await
        .unwrap();
    tracing::info!("Active Learning Worker listening on port 3001");
    axum::serve(listener, app).await.unwrap();
}

async fn health_check(
    axum::extract::State(state): axum::extract::State<AppState>,
) -> Json<serde_json::Value> {
    let db_status = match &state.db {
        Some(pool) => match pool.get_stats().await {
            Ok(stats) => json!({
                "connected": true,
                "total": stats.total,
                "pending": stats.pending,
                "accepted": stats.accepted,
                "rejected": stats.rejected,
                "maybe": stats.maybe,
            }),
            Err(e) => json!({"connected": false, "error": e.to_string()}),
        },
        None => json!({"connected": false, "error": "BD no configurada"}),
    };

    Json(json!({
        "status": "ok",
        "service": "active_learning_worker",
        "database": db_status,
        "ml_worker": "active",
    }))
}
