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

#[cfg(test)]
mod tests {
    use super::*;
    use ndarray::Array1;

    #[test]
    fn test_uncertainty_at_05_is_max() {
        assert!((uncertainty(0.5) - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_uncertainty_at_0_or_1_is_min() {
        assert!((uncertainty(0.0) - 0.0).abs() < 1e-10);
        assert!((uncertainty(1.0) - 0.0).abs() < 1e-10);
    }

    #[test]
    fn test_uncertainty_clamps_out_of_range() {
        assert!((uncertainty(-0.5) - 0.0).abs() < 1e-10);
        assert!((uncertainty(1.5) - 0.0).abs() < 1e-10);
    }

    #[test]
    fn test_compute_scores_uncertainty() {
        let probs = Array1::from_vec(vec![0.9, 0.5, 0.1]);
        let scores = compute_scores(&probs, AcquisitionStrategy::Uncertainty);
        // 0.5 should be first (highest uncertainty)
        assert_eq!(scores[0].0, 1);
        // 0.9 and 0.1 should tie (same uncertainty)
        assert!(scores[1].0 == 0 || scores[1].0 == 2);
    }

    #[test]
    fn test_compute_scores_most_relevant() {
        let probs = Array1::from_vec(vec![0.9, 0.5, 0.1]);
        let scores = compute_scores(&probs, AcquisitionStrategy::MostRelevant);
        assert_eq!(scores[0].0, 0); // 0.9 first
        assert_eq!(scores[1].0, 1); // 0.5 second
        assert_eq!(scores[2].0, 2); // 0.1 last
    }

    #[test]
    fn test_compute_scores_balanced() {
        let probs = Array1::from_vec(vec![0.9, 0.5, 0.1]);
        let scores = compute_scores(&probs, AcquisitionStrategy::Balanced);
        // 0.5 should rank highest (max uncertainty + moderate relevance)
        assert_eq!(scores[0].0, 1);
    }

    #[test]
    fn test_strategy_from_str() {
        assert_eq!(AcquisitionStrategy::from_str("uncertainty"), AcquisitionStrategy::Uncertainty);
        assert_eq!(AcquisitionStrategy::from_str("most_relevant"), AcquisitionStrategy::MostRelevant);
        assert_eq!(AcquisitionStrategy::from_str("relevant"), AcquisitionStrategy::MostRelevant);
        assert_eq!(AcquisitionStrategy::from_str("balanced"), AcquisitionStrategy::Balanced);
        assert_eq!(AcquisitionStrategy::from_str("anything"), AcquisitionStrategy::Balanced);
    }
}
