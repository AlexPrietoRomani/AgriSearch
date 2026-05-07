/// Integration tests for the Active Learning Worker.
///
/// Tests the full pipeline: DB operations → ML prediction → priority updates.
use std::fs;
use std::path::Path;

use active_learning_worker::db::{DbPool, DecisionStatus};
use active_learning_worker::ml::prototypical::predict_prototypical;

/// Creates a temporary test database with sample articles and embeddings.
fn setup_test_db() -> (DbPool, String) {
    use std::sync::atomic::{AtomicU64, Ordering};
    static COUNTER: AtomicU64 = AtomicU64::new(0);
    let id = COUNTER.fetch_add(1, Ordering::SeqCst);

    let db_path = format!("test_db_{}.sqlite", id);

    // Clean up if exists from a previous run
    cleanup_test_db(&db_path);

    let pool = DbPool::open(&db_path).expect("Failed to open test DB");

    // Create tables and insert test data synchronously via tokio
    let pool_clone = pool.clone();
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async move {
        let conn = pool_clone.conn.lock().await;

        conn.execute_batch(
            "
            CREATE TABLE IF NOT EXISTS articles (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                abstract TEXT,
                keywords TEXT,
                status TEXT DEFAULT 'pending',
                priority_score REAL DEFAULT 0.0,
                suggestion_score REAL DEFAULT 0.0,
                uncertainty REAL DEFAULT 0.0
            );
            CREATE TABLE IF NOT EXISTS embeddings (
                article_id TEXT PRIMARY KEY,
                vector BLOB,
                FOREIGN KEY (article_id) REFERENCES articles(id)
            );
            ",
        )
        .expect("Failed to create tables");

        // Insert 12 articles: 4 accepted, 4 rejected, 4 pending
        let articles = [
            ("a1", "Accepted Paper 1", "abstract about crops", "wheat, yield"),
            ("a2", "Accepted Paper 2", "abstract about irrigation", "water, crops"),
            ("a3", "Accepted Paper 3", "abstract about soil", "soil, nutrients"),
            ("a4", "Accepted Paper 4", "abstract about pest control", "pest, organic"),
            ("r1", "Rejected Paper 1", "abstract about economics", "finance, market"),
            ("r2", "Rejected Paper 2", "abstract about policy", "law, regulation"),
            ("r3", "Rejected Paper 3", "abstract about history", "history, review"),
            ("r4", "Rejected Paper 4", "abstract about sociology", "society, culture"),
            ("p1", "Pending Paper 1", "abstract about agriculture ML", "AI, farming"),
            ("p2", "Pending Paper 2", "abstract about drone sensing", "drone, sensors"),
            ("p3", "Pending Paper 3", "abstract about climate change", "climate, weather"),
            ("p4", "Pending Paper 4", "abstract about genetics", "genes, CRISPR"),
        ];

        for (id, title, abstract_, keywords) in &articles {
            conn.execute(
                "INSERT INTO articles (id, title, abstract, keywords) VALUES (?1, ?2, ?3, ?4)",
                rusqlite::params![id, title, abstract_, keywords],
            )
            .expect("Failed to insert article");
        }

        // Mark accepted/rejected
        for id in &["a1", "a2", "a3", "a4"] {
            conn.execute(
                "UPDATE articles SET status = 'accepted' WHERE id = ?1",
                rusqlite::params![id],
            )
            .unwrap();
        }
        for id in &["r1", "r2", "r3", "r4"] {
            conn.execute(
                "UPDATE articles SET status = 'rejected' WHERE id = ?1",
                rusqlite::params![id],
            )
            .unwrap();
        }

        // Insert dummy 4-dim embeddings (instead of 384 for simplicity)
        // Accepted: cluster around [1, 1, 0, 0]
        // Rejected: cluster around [0, 0, 1, 1]
        // Pending: mixed positions
        let embeddings: &[(&str, &[f32])] = &[
            ("a1", &[1.0, 1.0, 0.0, 0.0]),
            ("a2", &[1.0, 0.9, 0.1, 0.0]),
            ("a3", &[0.9, 1.0, 0.0, 0.1]),
            ("a4", &[1.1, 0.9, 0.0, 0.0]),
            ("r1", &[0.0, 0.0, 1.0, 1.0]),
            ("r2", &[0.1, 0.0, 1.0, 0.9]),
            ("r3", &[0.0, 0.1, 0.9, 1.0]),
            ("r4", &[0.0, 0.0, 1.1, 0.9]),
            ("p1", &[0.8, 0.7, 0.2, 0.1]), // closer to accepted
            ("p2", &[0.5, 0.5, 0.5, 0.5]), // neutral
            ("p3", &[0.2, 0.1, 0.8, 0.7]), // closer to rejected
            ("p4", &[0.9, 0.8, 0.1, 0.2]), // closer to accepted
        ];

        for (id, vec) in embeddings {
            let bytes: Vec<u8> = vec.iter().flat_map(|v| v.to_ne_bytes()).collect();
            conn.execute(
                "INSERT INTO embeddings (article_id, vector) VALUES (?1, ?2)",
                rusqlite::params![id, bytes],
            )
            .expect("Failed to insert embedding");
        }
    });

    (pool, db_path)
}

fn cleanup_test_db(path: &str) {
    if Path::new(path).exists() {
        fs::remove_file(path).ok();
    }
    // Also remove WAL/SHM files
    let _ = fs::remove_file(format!("{}-wal", path));
    let _ = fs::remove_file(format!("{}-shm", path));
}

#[test]
fn test_db_get_next_article_returns_highest_priority() {
    let (pool, db_path) = setup_test_db();
    let rt = tokio::runtime::Runtime::new().unwrap();

    rt.block_on(async {
        // Set different priorities for pending articles
        let conn = pool.conn.lock().await;
        conn.execute(
            "UPDATE articles SET priority_score = 0.3 WHERE id = 'p1'",
            [],
        )
        .unwrap();
        conn.execute(
            "UPDATE articles SET priority_score = 0.9 WHERE id = 'p2'",
            [],
        )
        .unwrap();
        conn.execute(
            "UPDATE articles SET priority_score = 0.1 WHERE id = 'p3'",
            [],
        )
        .unwrap();
        conn.execute(
            "UPDATE articles SET priority_score = 0.5 WHERE id = 'p4'",
            [],
        )
        .unwrap();
        drop(conn);

        let article = pool.get_next_article().await.unwrap();
        assert!(article.is_some());
        let article = article.unwrap();
        assert_eq!(article.id, "p2"); // highest priority
        assert_eq!(article.status, "pending");
    });

    cleanup_test_db(&db_path);
}

#[test]
fn test_db_update_decision() {
    let (pool, db_path) = setup_test_db();
    let rt = tokio::runtime::Runtime::new().unwrap();

    rt.block_on(async {
        pool.update_decision("p1", &DecisionStatus::Accepted)
            .await
            .unwrap();

        let stats = pool.get_stats().await.unwrap();
        assert_eq!(stats.accepted, 5); // 4 original + 1 new
        assert_eq!(stats.pending, 3); // 4 - 1
    });

    cleanup_test_db(&db_path);
}

#[test]
fn test_db_get_stats() {
    let (pool, db_path) = setup_test_db();
    let rt = tokio::runtime::Runtime::new().unwrap();

    rt.block_on(async {
        let stats = pool.get_stats().await.unwrap();
        assert_eq!(stats.total, 12);
        assert_eq!(stats.accepted, 4);
        assert_eq!(stats.rejected, 4);
        assert_eq!(stats.pending, 4);
        assert_eq!(stats.maybe, 0);
    });

    cleanup_test_db(&db_path);
}

#[test]
fn test_db_get_labeled_embeddings() {
    let (pool, db_path) = setup_test_db();
    let rt = tokio::runtime::Runtime::new().unwrap();

    rt.block_on(async {
        let (features, labels) = pool.get_labeled_embeddings().await.unwrap();
        assert_eq!(features.nrows(), 8); // 4 accepted + 4 rejected
        assert_eq!(features.ncols(), 4); // 4-dim embeddings
        assert_eq!(labels.len(), 8);
        // 4 accepted (1) + 4 rejected (0)
        assert_eq!(labels.sum(), 4);
    });

    cleanup_test_db(&db_path);
}

#[test]
fn test_db_get_pending_embeddings() {
    let (pool, db_path) = setup_test_db();
    let rt = tokio::runtime::Runtime::new().unwrap();

    rt.block_on(async {
        let (ids, features) = pool.get_pending_embeddings().await.unwrap();
        assert_eq!(ids.len(), 4);
        assert_eq!(features.nrows(), 4);
        assert_eq!(features.ncols(), 4);
        assert!(ids.contains(&"p1".to_string()));
        assert!(ids.contains(&"p4".to_string()));
    });

    cleanup_test_db(&db_path);
}

#[test]
fn test_db_update_priorities() {
    let (pool, db_path) = setup_test_db();
    let rt = tokio::runtime::Runtime::new().unwrap();

    rt.block_on(async {
        let rankings = vec![
            ("p1".to_string(), 0.9, 0.8, 0.2),
            ("p2".to_string(), 0.5, 0.5, 0.8),
            ("p3".to_string(), 0.1, 0.2, 0.4),
            ("p4".to_string(), 0.7, 0.6, 0.3),
        ];
        pool.update_priorities(&rankings).await.unwrap();

        let article = pool.get_next_article().await.unwrap().unwrap();
        assert_eq!(article.id, "p1"); // highest priority_score = 0.9
        assert!((article.priority_score - 0.9).abs() < 1e-10);
    });

    cleanup_test_db(&db_path);
}

#[test]
fn test_db_get_next_article_returns_none_when_all_decided() {
    let (pool, db_path) = setup_test_db();
    let rt = tokio::runtime::Runtime::new().unwrap();

    rt.block_on(async {
        // Mark all pending as decided
        for id in &["p1", "p2", "p3", "p4"] {
            pool.update_decision(id, &DecisionStatus::Rejected)
                .await
                .unwrap();
        }

        let article = pool.get_next_article().await.unwrap();
        assert!(article.is_none());
    });

    cleanup_test_db(&db_path);
}

#[test]
fn test_prototypical_with_real_embeddings() {
    let (pool, db_path) = setup_test_db();
    let rt = tokio::runtime::Runtime::new().unwrap();

    rt.block_on(async {
        let (labeled_features, labeled_labels) = pool.get_labeled_embeddings().await.unwrap();
        let (_ids, pending_features) = pool.get_pending_embeddings().await.unwrap();

        let probs = predict_prototypical(&labeled_features, &labeled_labels, &pending_features);

        assert_eq!(probs.len(), 4);
        // All probabilities should be in [0, 1]
        for i in 0..probs.len() {
            assert!(probs[i] >= 0.0 && probs[i] <= 1.0);
        }
    });

    cleanup_test_db(&db_path);
}

#[test]
fn test_decision_status_from_str() {
    assert_eq!(DecisionStatus::from_str("accepted"), DecisionStatus::Accepted);
    assert_eq!(DecisionStatus::from_str("include"), DecisionStatus::Accepted);
    assert_eq!(DecisionStatus::from_str("rejected"), DecisionStatus::Rejected);
    assert_eq!(DecisionStatus::from_str("exclude"), DecisionStatus::Rejected);
    assert_eq!(DecisionStatus::from_str("maybe"), DecisionStatus::Maybe);
    assert_eq!(DecisionStatus::from_str("anything"), DecisionStatus::Maybe);
}

#[test]
fn test_decision_status_as_str() {
    assert_eq!(DecisionStatus::Accepted.as_str(), "accepted");
    assert_eq!(DecisionStatus::Rejected.as_str(), "rejected");
    assert_eq!(DecisionStatus::Maybe.as_str(), "maybe");
}
