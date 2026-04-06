import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

import pytest
from app.services.active_learning_service import ActiveLearningService
from app.models.project import ScreeningDecisionStatus

@pytest.fixture
def service():
    return ActiveLearningService()

@pytest.fixture
def labeled_data():
    return [
        {"title": "Wheat growth under UV-B radiation", "abstract": "Study on wheat and UV impact.", "keywords": "wheat, uv, growth", "decision": ScreeningDecisionStatus.INCLUDE},
        {"title": "Pest management in corn fields", "abstract": "Biological control of corn pests.", "keywords": "corn, pests, biocontrol", "decision": ScreeningDecisionStatus.INCLUDE},
        {"title": "Urban architecture and sustainability", "abstract": "Design of efficient buildings.", "keywords": "architecture, urban", "decision": ScreeningDecisionStatus.EXCLUDE},
        {"title": "Social behavior in urban transit", "abstract": "How people behave in buses.", "keywords": "transit, social", "decision": ScreeningDecisionStatus.EXCLUDE},
    ]

@pytest.fixture
def pool_data():
    return [
        {"title": "Effect of UV-C on wheat seeds", "abstract": "New study on seeds and radiation."}, # Likely Include
        {"title": "Urban sociology of public parks", "abstract": "Sociological study of parks."}, # Likely Exclude
        {"title": "Unclear study of plant biology", "abstract": "Mixed results on urban plants."}  # Likely Uncertain
    ]

def test_active_learning_train_fail_identical(service):
    """Test training fails if only one class is present."""
    bad_labels = [{"title": "t", "decision": ScreeningDecisionStatus.INCLUDE}] * 5
    assert service.train(bad_labels) is False

def test_active_learning_workflow(service, labeled_data, pool_data):
    """Test full training and prediction cycle."""
    # 1. Train
    success = service.train(labeled_data)
    assert success is True
    assert service._is_trained is True

    # 2. Predict
    results = service.predict_relevance(pool_data)
    
    assert len(results) == 3
    assert "suggestion_score" in results[0]
    assert "uncertainty" in results[0]

    # 3. Check specific predictions (prob of inclusion)
    # Wheat seed (1st) should have higher score than Urban sociology (2nd)
    assert results[0]["suggestion_score"] > results[1]["suggestion_score"]
    
    # 4. Check ranking modes
    # Most relevant first
    ranked_relevant = service.rank_for_screening(results, mode="most_relevant")
    assert ranked_relevant[0]["title"] == "Effect of UV-C on wheat seeds"
    
    # Most uncertain first
    # This identifies where the model is least confident (close to 0.5)
    # The article closest to 0.5 prob should have highest uncertainty
    ranked_uncertain = service.rank_for_screening(results, mode="uncertainty")
    assert "uncertainty" in ranked_uncertain[0]
