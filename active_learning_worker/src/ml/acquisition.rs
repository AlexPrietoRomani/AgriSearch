/// Funciones de adquisicion para Active Learning.
///
/// Tres estrategias:
/// - `uncertainty`: prioriza articulos mas dudosos (exploracion)
/// - `most_relevant`: prioriza mayor P(include) (explotacion)
/// - `balanced`: combinacion ponderada 50/50
use ndarray::Array1;

/// Ranking strategy.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum AcquisitionStrategy {
    Uncertainty,
    MostRelevant,
    Balanced,
}

impl AcquisitionStrategy {
    pub fn from_str(s: &str) -> Self {
        match s {
            "uncertainty" => AcquisitionStrategy::Uncertainty,
            "most_relevant" | "relevant" => AcquisitionStrategy::MostRelevant,
            _ => AcquisitionStrategy::Balanced,
        }
    }
}

/// Calcula score de adquisicion para cada articulo pendiente.
///
/// Retorna vec de (index, score) ordenado descendente por score.
pub fn compute_scores(
    probabilities: &Array1<f64>,
    strategy: AcquisitionStrategy,
) -> Vec<(usize, f64)> {
    let n = probabilities.len();
    let mut scores: Vec<(usize, f64)> = Vec::with_capacity(n);

    for i in 0..n {
        let p = probabilities[i].clamp(0.0, 1.0);
        let score = match strategy {
            AcquisitionStrategy::Uncertainty => {
                // Mayor incertidumbre = mas cercano a 0.5
                1.0 - 2.0 * (p - 0.5).abs()
            }
            AcquisitionStrategy::MostRelevant => {
                // Mayor probabilidad de inclusion
                p
            }
            AcquisitionStrategy::Balanced => {
                // 50% exploracion + 50% explotacion
                let uncertainty = 1.0 - 2.0 * (p - 0.5).abs();
                0.5 * uncertainty + 0.5 * p
            }
        };
        scores.push((i, score));
    }

    // Ordenar descendente por score
    scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    scores
}

/// Calcula incertidumbre individual para un articulo.
pub fn uncertainty(p: f64) -> f64 {
    1.0 - 2.0 * (p.clamp(0.0, 1.0) - 0.5).abs()
}
