"""
Archivo: test_active_learning.py
Modificación: 2026-05-06
Autor: Alex Prieto

Descripción:
Pruebas unitarias para el servicio de Aprendizaje Activo (`ActiveLearningService`).
Valida el ciclo de entrenamiento, predicción de relevancia y ranking de artículos
para optimizar el proceso de cribado (screening) sistemático.

Acciones Principales:
    - Validación de fallo controlado cuando los datos de entrenamiento son insuficientes o uniformes.
    - Prueba del flujo completo: Entrenamiento -> Predicción -> Ranking.
    - Verificación de la consistencia de los scores de sugerencia y métricas de incertidumbre.
    - Comprobación de los modos de ranking: "most_relevant" (explotación) y "uncertainty" (exploración).

Entradas / Dependencias:
    - Datos etiquetados de ejemplo (Include/Exclude).
    - Pool de artículos sin etiquetar.
    - `ActiveLearningService` del backend.

Ejemplo de Ejecución:
    pytest tests/backend/unit/test_active_learning.py
"""

import os
import sys

# Agregar backend al path para resolver importaciones
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

import pytest
from app.models.project import ScreeningDecisionStatus
from app.services.active_learning_service import ActiveLearningService


@pytest.fixture
def service() -> ActiveLearningService:
    """Provee una instancia limpia del servicio de Active Learning."""
    return ActiveLearningService()


@pytest.fixture
def labeled_data() -> list:
    """Provee un conjunto de datos etiquetados balanceado para entrenamiento."""
    return [
        {
            "title": "Wheat growth under UV-B radiation", 
            "abstract": "Study on wheat and UV impact.", 
            "keywords": "wheat, uv, growth", 
            "decision": ScreeningDecisionStatus.INCLUDE
        },
        {
            "title": "Pest management in corn fields", 
            "abstract": "Biological control of corn pests.", 
            "keywords": "corn, pests, biocontrol", 
            "decision": ScreeningDecisionStatus.INCLUDE
        },
        {
            "title": "Urban architecture and sustainability", 
            "abstract": "Design of efficient buildings.", 
            "keywords": "architecture, urban", 
            "decision": ScreeningDecisionStatus.EXCLUDE
        },
        {
            "title": "Social behavior in urban transit", 
            "abstract": "How people behave in buses.", 
            "keywords": "transit, social", 
            "decision": ScreeningDecisionStatus.EXCLUDE
        },
    ]


@pytest.fixture
def pool_data() -> list:
    """Provee un pool de artículos sin etiquetar para predicción."""
    return [
        {"title": "Effect of UV-C on wheat seeds", "abstract": "New study on seeds and radiation."},
        {"title": "Urban sociology of public parks", "abstract": "Sociological study of parks."},
        {"title": "Unclear study of plant biology", "abstract": "Mixed results on urban plants."}
    ]


def test_active_learning_train_fail_identical(service: ActiveLearningService):
    """
    Verifica que el entrenamiento falle si solo hay una clase presente (Include o Exclude).
    """
    bad_labels = [{"title": "t", "decision": ScreeningDecisionStatus.INCLUDE}] * 5
    assert service.train(bad_labels) is False


def test_active_learning_workflow(service: ActiveLearningService, labeled_data: list, pool_data: list):
    """
    Verifica el ciclo completo de entrenamiento y predicción.
    """
    # 1. Entrenar el modelo
    success = service.train(labeled_data)
    assert success is True
    assert service._is_trained is True

    # 2. Predecir relevancia sobre el pool
    results = service.predict_relevance(pool_data)
    
    assert len(results) == 3
    assert "suggestion_score" in results[0]
    assert "uncertainty" in results[0]

    # 3. Validar consistencia de predicciones (Probabilidad de inclusión)
    # El estudio sobre trigo (relevante) debe tener mayor score que el de sociología urbana.
    assert results[0]["suggestion_score"] > results[1]["suggestion_score"]
    
    # 4. Validar modos de ranking
    # Modo: Más relevantes primero
    ranked_relevant = service.rank_for_screening(results, mode="most_relevant")
    assert ranked_relevant[0]["title"] == "Effect of UV-C on wheat seeds"
    
    # Modo: Mayor incertidumbre primero (muestreo para mejorar el modelo)
    ranked_uncertain = service.rank_for_screening(results, mode="uncertainty")
    assert "uncertainty" in ranked_uncertain[0]
