pub mod db;

use axum::{routing::get, Router, Json};
use serde_json::json;
use tower_http::cors::{Any, CorsLayer};

use crate::db::DbPool;

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

    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    let app = Router::new()
        .route("/health", get(health_check))
        .layer(cors)
        .with_state(db);

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3001")
        .await
        .unwrap();
    tracing::info!("Active Learning Worker listening on port 3001");
    axum::serve(listener, app).await.unwrap();
}

async fn health_check(
    axum::extract::State(db): axum::extract::State<Option<DbPool>>,
) -> Json<serde_json::Value> {
    let db_status = match &db {
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
    }))
}
