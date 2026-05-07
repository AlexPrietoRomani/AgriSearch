/// Redes Prototipicas para cold start (<20 etiquetas).
///
/// Algoritmo:
/// 1. Calcular centroide de embeddings aceptados
/// 2. Calcular centroide de embeddings rechazados
/// 3. Para cada pendiente: distancia euclidiana a ambos centroides
/// 4. Softmax sobre distancias negativas -> P(include)
/// 5. Incertidumbre = 1 - 2*|p - 0.5|
///
/// Complejidad: O(N * d) donde N=pendientes, d=384 dimensiones.
use ndarray::{Array1, Array2};

/// Calcula probabilidades de inclusion via Redes Prototipicas.
///
/// Retorna Array1 de probabilidades [0, 1] para cada articulo pendiente.
pub fn predict_prototypical(
    labeled_features: &Array2<f32>,
    labeled_labels: &Array1<i32>,
    pending_features: &Array2<f32>,
) -> Array1<f64> {
    let n_pending = pending_features.nrows();
    let n_labeled = labeled_features.nrows();

    if n_pending == 0 {
        return Array1::zeros(0);
    }

    // Separar embeddings por clase (clonar para evitar problemas de lifetime)
    let mut accepted_vecs: Vec<Vec<f32>> = Vec::new();
    let mut rejected_vecs: Vec<Vec<f32>> = Vec::new();

    for i in 0..n_labeled {
        let row = labeled_features.row(i);
        let vec: Vec<f32> = row.as_slice().unwrap().to_vec();
        if labeled_labels[i] == 1 {
            accepted_vecs.push(vec);
        } else {
            rejected_vecs.push(vec);
        }
    }

    // Calcular centroides
    let d = labeled_features.ncols();
    let accepted_centroid = compute_centroid(&accepted_vecs, d);
    let rejected_centroid = compute_centroid(&rejected_vecs, d);

    // Calcular distancias y probabilidades
    let mut probs = Array1::zeros(n_pending);

    for i in 0..n_pending {
        let row = pending_features.row(i);
        let vec: Vec<f32> = row.as_slice().unwrap().to_vec();

        let dist_accepted = euclidean_distance(&vec, &accepted_centroid);
        let dist_rejected = euclidean_distance(&vec, &rejected_centroid);

        // Softmax sobre distancias negativas
        // P(include) = exp(-dist_accepted) / (exp(-dist_accepted) + exp(-dist_rejected))
        let exp_neg_acc = (-dist_accepted).exp();
        let exp_neg_rej = (-dist_rejected).exp();
        let denom = exp_neg_acc + exp_neg_rej;

        let p = if denom > 0.0 {
            exp_neg_acc / denom
        } else {
            0.5 // Sin informacion -> neutral
        };

        probs[i] = p.clamp(0.0, 1.0);
    }

    probs
}

/// Calcula centroide (media aritmetica) de un conjunto de vectores.
fn compute_centroid(vectors: &[Vec<f32>], dim: usize) -> Vec<f32> {
    if vectors.is_empty() {
        return vec![0.0; dim];
    }

    let mut centroid = vec![0.0f32; dim];
    let n = vectors.len() as f32;

    for vec in vectors {
        for (i, &val) in vec.iter().enumerate() {
            centroid[i] += val;
        }
    }

    for c in centroid.iter_mut() {
        *c /= n;
    }

    centroid
}

/// Distancia euclidiana entre dos vectores.
fn euclidean_distance(a: &[f32], b: &[f32]) -> f64 {
    let mut sum = 0.0f64;
    for (&ai, &bi) in a.iter().zip(b.iter()) {
        let diff = (ai as f64) - (bi as f64);
        sum += diff * diff;
    }
    sum.sqrt()
}
