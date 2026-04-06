# -*- coding: utf-8 -*-
"""
Tests unitarios para la construcción del Grafo de Relación Temática.

Fase 4 — Sub-fase 4.3: Construcción del Grafo de Relación Temática
Valida el cálculo de similitud semántica entre artículos, la extracción
de keywords compartidas, y la correcta aplicación del umbral de corte.

Ejecución:
    pytest tests/unit/test_thematic_graph.py -v
"""

import pytest
import numpy as np


# ──────────────────────────────────────────────
# Datos de prueba con embeddings simulados
# ──────────────────────────────────────────────

# Vectores de ejemplo normalizados (768d reducidos a 8d para tests)
ARTICLE_EMBEDDINGS = {
    "10.1016/j.compag.2023.107500": {
        "title": "YOLO-based crop phenology detection",
        "vector": np.array([0.8, 0.6, 0.1, 0.9, 0.3, 0.7, 0.2, 0.5]),
        "topics": ["YOLO", "fenología", "detección de objetos", "agricultura de precisión", "drones"],
    },
    "10.3390/rs14153690": {
        "title": "Remote sensing for crop monitoring",
        "vector": np.array([0.7, 0.5, 0.2, 0.85, 0.4, 0.65, 0.15, 0.55]),
        "topics": ["teledetección", "machine learning", "monitoreo cultivos", "clasificación", "drones"],
    },
    "10.1007/s11119-022-09876-5": {
        "title": "UAV-based wheat disease detection",
        "vector": np.array([0.3, 0.8, 0.7, 0.2, 0.9, 0.1, 0.6, 0.4]),
        "topics": ["UAV", "multiespectral", "trigo", "enfermedades", "deep learning"],
    },
    "10.1016/j.biosystemseng.2021.04.012": {
        "title": "Transfer learning for plant disease identification",
        "vector": np.array([0.25, 0.75, 0.65, 0.15, 0.85, 0.2, 0.55, 0.45]),
        "topics": ["transfer learning", "CNN", "enfermedades vegetales", "identificación", "deep learning"],
    },
    "10.1016/j.fcr.2020.107852": {
        "title": "Automated phenotyping of field crops",
        "vector": np.array([0.75, 0.55, 0.15, 0.88, 0.35, 0.68, 0.18, 0.52]),
        "topics": ["fenotipado", "drones", "cultivos campo", "automatización", "agricultura de precisión"],
    },
}


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calcula la similitud coseno entre dos vectores."""
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def extract_shared_keywords(topics_a: list, topics_b: list) -> list:
    """Extrae las keywords compartidas entre dos listas de temas."""
    return list(set(topics_a) & set(topics_b))


# ──────────────────────────────────────────────
# Tests de similitud semántica
# ──────────────────────────────────────────────

class TestCosineSimilarity:
    """Tests para el cálculo de cosine similarity entre embeddings."""

    def test_identical_vectors_similarity_one(self):
        """Vectores idénticos tienen similitud 1.0."""
        v = np.array([0.5, 0.5, 0.5, 0.5])
        assert cosine_similarity(v, v) == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_vectors_similarity_zero(self):
        """Vectores ortogonales tienen similitud 0.0."""
        a = np.array([1.0, 0.0, 0.0, 0.0])
        b = np.array([0.0, 1.0, 0.0, 0.0])
        assert cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-6)

    def test_zero_vector_returns_zero(self):
        """Un vector nulo retorna similitud 0.0."""
        a = np.array([0.5, 0.5])
        b = np.array([0.0, 0.0])
        assert cosine_similarity(a, b) == 0.0

    def test_similar_articles_high_similarity(self):
        """Artículos temáticamente similares deben tener alta similitud."""
        phenology = ARTICLE_EMBEDDINGS["10.1016/j.compag.2023.107500"]["vector"]
        remote_sensing = ARTICLE_EMBEDDINGS["10.3390/rs14153690"]["vector"]
        sim = cosine_similarity(phenology, remote_sensing)
        # Ambos son sobre agricultura de precisión con deep learning
        assert sim > 0.90, f"Similitud esperada > 0.90, obtenida: {sim:.4f}"

    def test_dissimilar_articles_lower_similarity(self):
        """Artículos de dominios distintos deben tener menor similitud."""
        phenology = ARTICLE_EMBEDDINGS["10.1016/j.compag.2023.107500"]["vector"]
        disease = ARTICLE_EMBEDDINGS["10.1007/s11119-022-09876-5"]["vector"]
        sim = cosine_similarity(phenology, disease)
        # Fenología vs enfermedades — diferentes subdominios
        assert sim < 0.95, f"Similitud esperada < 0.95, obtenida: {sim:.4f}"


# ──────────────────────────────────────────────
# Tests de umbral de corte
# ──────────────────────────────────────────────

class TestThresholdFiltering:
    """Tests para la aplicación del umbral de similitud al construir aristas."""

    @pytest.fixture
    def similarity_matrix(self):
        """Calcula la matriz de similitud entre todos los artículos."""
        dois = list(ARTICLE_EMBEDDINGS.keys())
        n = len(dois)
        matrix = {}
        for i in range(n):
            for j in range(i + 1, n):
                sim = cosine_similarity(
                    ARTICLE_EMBEDDINGS[dois[i]]["vector"],
                    ARTICLE_EMBEDDINGS[dois[j]]["vector"],
                )
                matrix[(dois[i], dois[j])] = sim
        return matrix

    def test_default_threshold_filters_edges(self, similarity_matrix):
        """Con umbral 0.75, solo se crean aristas para pares suficientemente similares."""
        threshold = 0.75
        edges = [
            (pair, sim)
            for pair, sim in similarity_matrix.items()
            if sim >= threshold
        ]
        # Debe haber al menos 1 arista (los artículos de agricultura de precisión)
        assert len(edges) >= 1
        # Todas las aristas deben superar el umbral
        for _, sim in edges:
            assert sim >= threshold

    def test_strict_threshold_reduces_edges(self, similarity_matrix):
        """Un umbral más estricto (0.95) produce menos aristas."""
        edges_075 = [s for s in similarity_matrix.values() if s >= 0.75]
        edges_095 = [s for s in similarity_matrix.values() if s >= 0.95]
        assert len(edges_095) <= len(edges_075)

    def test_zero_threshold_connects_all(self, similarity_matrix):
        """Con umbral 0.0 todos los pares están conectados."""
        edges = [s for s in similarity_matrix.values() if s >= 0.0]
        n_articles = len(ARTICLE_EMBEDDINGS)
        expected_pairs = n_articles * (n_articles - 1) // 2
        assert len(edges) == expected_pairs


# ──────────────────────────────────────────────
# Tests de keywords compartidas
# ──────────────────────────────────────────────

class TestSharedKeywords:
    """Tests para la extracción de keywords compartidas entre artículos."""

    def test_shared_keywords_between_similar_articles(self):
        """Artículos similares deben compartir keywords."""
        topics_a = ARTICLE_EMBEDDINGS["10.1016/j.compag.2023.107500"]["topics"]
        topics_b = ARTICLE_EMBEDDINGS["10.1016/j.fcr.2020.107852"]["topics"]
        shared = extract_shared_keywords(topics_a, topics_b)
        # Ambos mencionan "drones" y "agricultura de precisión"
        assert "drones" in shared
        assert "agricultura de precisión" in shared

    def test_no_shared_keywords_returns_empty(self):
        """Artículos sin keywords en común retornan lista vacía."""
        topics_a = ["YOLO", "fenología", "soja"]
        topics_b = ["genética", "biopesticida", "suelo"]
        shared = extract_shared_keywords(topics_a, topics_b)
        assert len(shared) == 0

    def test_shared_keywords_are_unique(self):
        """No debe haber duplicados en las keywords compartidas."""
        topics_a = ["ML", "drones", "ML", "cultivos"]
        topics_b = ["drones", "drones", "ML"]
        shared = extract_shared_keywords(topics_a, topics_b)
        assert len(shared) == len(set(shared))


# ──────────────────────────────────────────────
# Tests de construcción del grafo temático
# ──────────────────────────────────────────────

class TestThematicGraphConstruction:
    """Tests para la construcción del grafo temático con NetworkX."""

    @pytest.fixture
    def thematic_graph(self):
        """Construye un grafo temático de prueba."""
        import networkx as nx

        G = nx.Graph()  # No dirigido
        threshold = 0.75

        dois = list(ARTICLE_EMBEDDINGS.keys())

        # Añadir nodos
        for doi, data in ARTICLE_EMBEDDINGS.items():
            G.add_node(doi, title=data["title"], topics=data["topics"])

        # Añadir aristas por similitud
        for i in range(len(dois)):
            for j in range(i + 1, len(dois)):
                sim = cosine_similarity(
                    ARTICLE_EMBEDDINGS[dois[i]]["vector"],
                    ARTICLE_EMBEDDINGS[dois[j]]["vector"],
                )
                if sim >= threshold:
                    shared = extract_shared_keywords(
                        ARTICLE_EMBEDDINGS[dois[i]]["topics"],
                        ARTICLE_EMBEDDINGS[dois[j]]["topics"],
                    )
                    G.add_edge(
                        dois[i],
                        dois[j],
                        cosine_similarity=sim,
                        shared_keywords=shared,
                    )

        return G

    def test_graph_is_undirected(self, thematic_graph):
        """El grafo temático debe ser no dirigido."""
        assert not thematic_graph.is_directed()

    def test_all_included_articles_are_nodes(self, thematic_graph):
        """Todos los artículos incluidos deben ser nodos del grafo."""
        for doi in ARTICLE_EMBEDDINGS:
            assert doi in thematic_graph.nodes

    def test_edges_have_similarity_score(self, thematic_graph):
        """Cada arista debe tener un cosine_similarity score."""
        for u, v, data in thematic_graph.edges(data=True):
            assert "cosine_similarity" in data
            assert 0.0 <= data["cosine_similarity"] <= 1.0

    def test_edges_have_shared_keywords(self, thematic_graph):
        """Cada arista debe tener una lista de shared_keywords."""
        for u, v, data in thematic_graph.edges(data=True):
            assert "shared_keywords" in data
            assert isinstance(data["shared_keywords"], list)
