/// Endpoints REST para el Active Learning Worker.
///
/// Implementa las rutas:
/// - POST /decide   — Registra decision y retorna siguiente articulo
/// - GET  /next     — Retorna el articulo con mayor prioridad
/// - GET  /status   — Estadisticas de screening
/// - GET  /progress — Datos para grafico de progreso
use axum::{
    extract::State,
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::sync::atomic::{AtomicU64, Ordering};

use crate::db::DecisionStatus;
use crate::ml::acquisition::AcquisitionStrategy;
use crate::{AppState, TrainingTrigger};

/// Contador atomico de decisiones (compartido entre requests).
static DECISION_COUNTER: AtomicU64 = AtomicU64::new(0);

/// Request para registrar una decision.
#[derive(Deserialize)]
pub struct DecideRequest {
    pub id: String,
    pub status: String,
}

/// Respuesta con el siguiente articulo.
#[derive(Serialize)]
pub struct ArticleResponse {
    pub id: String,
    pub title: String,
    #[serde(rename = "abstract")]
    pub r#abstract: Option<String>,
    pub keywords: Option<String>,
    pub suggestion_score: f64,
    pub uncertainty: f64,
    pub retraining_triggered: bool,
}

/// Respuesta de estadisticas.
#[derive(Serialize)]
pub struct StatusResponse {
    pub total: i64,
    pub pending: i64,
    pub accepted: i64,
    pub rejected: i64,
    pub maybe: i64,
    pub progress_pct: f64,
    pub decisions_since_retrain: u64,
}

/// Respuesta de progreso para graficos.
#[derive(Serialize)]
pub struct ProgressResponse {
    pub decisions_over_time: Vec<ProgressPoint>,
}

#[derive(Serialize)]
pub struct ProgressPoint {
    pub count: i64,
    pub accepted: i64,
    pub rejected: i64,
}

/// Registra una decision y retorna el siguiente articulo.
/// Cada 10 decisiones dispara re-entrenamiento en background via mpsc.
pub async fn decide(
    State(state): State<AppState>,
    Json(req): Json<DecideRequest>,
) -> Result<Json<ArticleResponse>, (StatusCode, Json<serde_json::Value>)> {
    let pool = state.db.as_ref().ok_or((
        StatusCode::SERVICE_UNAVAILABLE,
        Json(json!({"error": "Base de datos no disponible"})),
    ))?;

    let status = DecisionStatus::from_str(&req.status);
    pool.update_decision(&req.id, &status)
        .await
        .map_err(|e| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({"error": e.to_string()})),
            )
        })?;

    tracing::info!("Decision registrada: {} -> {:?}", req.id, status);

    // Incrementar contador y verificar si toca re-entrenar
    let count = DECISION_COUNTER.fetch_add(1, Ordering::SeqCst) + 1;
    let retraining_triggered = if count % 10 == 0 {
        let trigger = TrainingTrigger::Retrain(AcquisitionStrategy::Balanced);
        match state.tx.try_send(trigger) {
            Ok(()) => {
                tracing::info!(
                    "Re-entrenamiento disparado (decision #{})",
                    count
                );
                true
            }
            Err(e) => {
                tracing::warn!("Canal mpsc lleno, re-entrenamiento omitido: {}", e);
                false
            }
        }
    } else {
        false
    };

    // Obtener siguiente articulo
    match pool.get_next_article().await {
        Ok(Some(article)) => Ok(Json(ArticleResponse {
            id: article.id,
            title: article.title,
            r#abstract: article.r#abstract,
            keywords: article.keywords,
            suggestion_score: article.suggestion_score,
            uncertainty: article.uncertainty,
            retraining_triggered,
        })),
        Ok(None) => Ok(Json(ArticleResponse {
            id: String::new(),
            title: String::from("No hay mas articulos pendientes"),
            r#abstract: None,
            keywords: None,
            suggestion_score: 0.0,
            uncertainty: 0.0,
            retraining_triggered,
        })),
        Err(e) => Err((
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"error": e.to_string()})),
        )),
    }
}

/// Retorna el siguiente articulo sin registrar decision.
pub async fn next(
    State(state): State<AppState>,
) -> Result<Json<ArticleResponse>, (StatusCode, Json<serde_json::Value>)> {
    let pool = state.db.as_ref().ok_or((
        StatusCode::SERVICE_UNAVAILABLE,
        Json(json!({"error": "Base de datos no disponible"})),
    ))?;

    match pool.get_next_article().await {
        Ok(Some(article)) => Ok(Json(ArticleResponse {
            id: article.id,
            title: article.title,
            r#abstract: article.r#abstract,
            keywords: article.keywords,
            suggestion_score: article.suggestion_score,
            uncertainty: article.uncertainty,
            retraining_triggered: false,
        })),
        Ok(None) => Ok(Json(ArticleResponse {
            id: String::new(),
            title: String::from("No hay mas articulos pendientes"),
            r#abstract: None,
            keywords: None,
            suggestion_score: 0.0,
            uncertainty: 0.0,
            retraining_triggered: false,
        })),
        Err(e) => Err((
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"error": e.to_string()})),
        )),
    }
}

/// Retorna estadisticas de screening.
pub async fn status(
    State(state): State<AppState>,
) -> Result<Json<StatusResponse>, (StatusCode, Json<serde_json::Value>)> {
    let pool = state.db.as_ref().ok_or((
        StatusCode::SERVICE_UNAVAILABLE,
        Json(json!({"error": "Base de datos no disponible"})),
    ))?;

    let stats = pool.get_stats().await.map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"error": e.to_string()})),
        )
    })?;

    let reviewed = stats.accepted + stats.rejected + stats.maybe;
    let progress_pct = if stats.total > 0 {
        (reviewed as f64 / stats.total as f64) * 100.0
    } else {
        0.0
    };

    let decisions_since_retrain = DECISION_COUNTER.load(Ordering::SeqCst) % 10;

    Ok(Json(StatusResponse {
        total: stats.total,
        pending: stats.pending,
        accepted: stats.accepted,
        rejected: stats.rejected,
        maybe: stats.maybe,
        progress_pct,
        decisions_since_retrain,
    }))
}

/// Retorna datos para grafico de progreso.
pub async fn progress(
    State(state): State<AppState>,
) -> Result<Json<ProgressResponse>, (StatusCode, Json<serde_json::Value>)> {
    let pool = state.db.as_ref().ok_or((
        StatusCode::SERVICE_UNAVAILABLE,
        Json(json!({"error": "Base de datos no disponible"})),
    ))?;

    let stats = pool.get_stats().await.map_err(|e| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({"error": e.to_string()})),
        )
    })?;

    // Snapshot actual como unico punto en el tiempo
    // (En produccion se podria loggear historial en una tabla separada)
    let decisions_over_time = vec![ProgressPoint {
        count: stats.accepted + stats.rejected + stats.maybe,
        accepted: stats.accepted,
        rejected: stats.rejected,
    }];

    Ok(Json(ProgressResponse {
        decisions_over_time,
    }))
}

/// Construye el router de la API.
pub fn router() -> Router<AppState> {
    Router::new()
        .route("/decide", post(decide))
        .route("/next", get(next))
        .route("/status", get(status))
        .route("/progress", get(progress))
}
