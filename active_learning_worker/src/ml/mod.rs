/// Motor de Machine Learning para Active Learning.
///
/// Dos estrategias:
/// - Redes Prototipicas: cold start (<20 etiquetas)
/// - Ridge Regression: regimen estable (20+ etiquetas)
///
/// Tres funciones de adquisicion:
/// - uncertainty: exploracion (articulos dudosos)
/// - most_relevant: explotacion (articulos prometedores)
/// - balanced: combinacion 50/50
pub mod acquisition;
pub mod linear;
pub mod prototypical;

use anyhow::Result;
use ndarray::Array1;

use crate::db::DbPool;
use acquisition::{compute_scores, AcquisitionStrategy};

/// Re-entrena modelo y actualiza prioridades en BD.
///
/// Flujo:
/// 1. Extraer embeddings etiquetados y pendientes
/// 2. Predecir P(include) con estrategia apropiada
/// 3. Calcular scores de adquisicion
/// 4. Actualizar prioridades en BD (transaccion atomica)
pub async fn retrain_and_rerank(
    db: &DbPool,
    strategy: AcquisitionStrategy,
) -> Result<usize> {
    let start = std::time::Instant::now();

    // 1. Extraer datos
    let (labeled_features, labeled_labels) = db.get_labeled_embeddings().await?;
    let (pending_ids, pending_features) = db.get_pending_embeddings().await?;

    let n_pending = pending_ids.len();
    if n_pending == 0 {
        tracing::info!("No hay articulos pendientes para re-rankear");
        return Ok(0);
    }

    let n_labeled = labeled_features.nrows();
    tracing::info!(
        "Re-entrenamiento: {} etiquetados, {} pendientes",
        n_labeled,
        n_pending
    );

    // 2. Predecir probabilidades
    let probabilities: Array1<f64> = if n_labeled >= 20 {
        // Ridge Regression para 20+ muestras
        match linear::predict_with_ridge(&labeled_features, &labeled_labels, &pending_features)? {
            Some(probs) => {
                tracing::info!("Usando Ridge Regression ({} muestras)", n_labeled);
                probs
            }
            None => {
                // Fallback a prototypical si Ridge falla
                tracing::warn!("Ridge fallo, fallback a prototypical");
                prototypical::predict_prototypical(&labeled_features, &labeled_labels, &pending_features)
            }
        }
    } else {
        // Prototypical Networks para cold start
        tracing::info!("Usando Redes Prototipicas ({} muestras)", n_labeled);
        prototypical::predict_prototypical(&labeled_features, &labeled_labels, &pending_features)
    };

    // 3. Calcular scores de adquisicion
    let scored = compute_scores(&probabilities, strategy);

    // 4. Construir rankings: (id, priority_score, suggestion_score, uncertainty)
    let mut rankings: Vec<(String, f64, f64, f64)> = Vec::with_capacity(n_pending);

    // scored esta ordenado descendente por score -> asignar prioridad inversa
    // El articulo con mayor score de adquisicion recibe priority_score mas alto
    for (idx, score) in scored.iter() {
        let id = pending_ids[*idx].clone();
        let p = probabilities[*idx];
        let unc = acquisition::uncertainty(p);

        // Priority: normalizar score a [0, 1] donde 1 = mas prioritario
        let priority = *score;
        let suggestion = p;

        rankings.push((id, priority, suggestion, unc));
    }

    // 5. Actualizar BD
    db.update_priorities(&rankings).await?;

    let elapsed = start.elapsed();
    tracing::info!(
        "Re-entrenamiento completado en {:.2}ms, {} articulos re-rankeados",
        elapsed.as_secs_f64() * 1000.0,
        n_pending
    );

    Ok(n_pending)
}
