/// Clasificador lineal via linfa para regimen estable (20+ etiquetas).
///
/// Usa Linear Regression de linfa-linear para predecir P(include).
/// Cuando hay pocas muestras (<20), retorna None y se usa prototypical.
use anyhow::{Context, Result};
use linfa::prelude::{Fit, Predict};
use linfa::Dataset;
use linfa_linear::LinearRegression;
use ndarray::{Array1, Array2};

/// Entrena clasificador Linear sobre embeddings etiquetados.
///
/// Retorna probabilidades para articulos pendientes.
/// None si hay <20 muestras etiquetadas.
pub fn predict_with_ridge(
    labeled_features: &Array2<f32>,
    labeled_labels: &Array1<i32>,
    pending_features: &Array2<f32>,
) -> Result<Option<Array1<f64>>> {
    let n_labeled = labeled_features.nrows();

    if n_labeled < 20 {
        return Ok(None);
    }

    // Convertir f32 -> f64 para linfa
    let features_f64 = labeled_features.mapv(|x| x as f64);
    let labels_f64 = labeled_labels.mapv(|x| x as f64);

    let dataset = Dataset::new(features_f64, labels_f64);

    // Entrenar Linear Regression (OLS)
    let model = LinearRegression::default()
        .fit(&dataset)
        .context("Failed to fit Linear Regression")?;

    // Predecir sobre pendientes
    let pending_f64 = pending_features.mapv(|x| x as f64);
    let predictions = model.predict(&Dataset::from(pending_f64));

    // Clamp a [0, 1] para interpretar como probabilidad
    let probs = predictions.mapv(|x| x.clamp(0.0, 1.0));

    Ok(Some(probs))
}
