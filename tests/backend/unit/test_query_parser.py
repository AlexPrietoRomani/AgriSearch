"""
Archivo: test_query_parser.py
Modificación: 2026-05-14
Autor: Antigravity

Descripción:
Pruebas unitarias para validar el análisis y descomposición de consultas booleanas maestras.
Verifica que la lógica de extracción de conceptos primarios y sinónimos sea robusta
frente a diferentes formatos de comillas, paréntesis y operadores AND/OR.

Acciones Principales:
    - Validar el parsing de queries con comillas dobles y simples.
    - Verificar la correcta separación de grupos conceptuales (AND de nivel superior).
    - Comprobar la extracción de términos alternativos (OR) dentro de cada grupo.
    - Validar la limpieza de filtros de fecha embebidos en la query.

Estructura Interna:
    - `test_parse_complex_boolean_query`: Prueba una query exhaustiva con múltiples sinónimos.
    - `test_parse_single_quotes_query`: Verifica el soporte para comillas simples.
    - `test_parse_query_with_date_range`: Asegura que los rangos (YYYY:YYYY) sean ignorados.

Ejecución:
    uv run pytest tests/backend/unit/test_query_parser.py
"""

import pytest
from app.services.search_service import _parse_boolean_query_structure

def test_parse_complex_boolean_query():
    """Valida el parsing de una query booleana estándar con comillas dobles."""
    q = (
        '(ViT OR "Vision Transformer" OR "Transformer model") AND '
        '(CNN OR "Convolutional Neural Network" OR ConvNet) AND '
        '(agriculture OR "precision agriculture" OR agronomy)'
    )
    concepts, synonyms = _parse_boolean_query_structure(q)
    
    assert "ViT" in concepts
    assert "CNN" in concepts
    assert "agriculture" in concepts
    assert "Vision Transformer" in synonyms["ViT"]
    assert "Convolutional Neural Network" in synonyms["CNN"]
    assert "precision agriculture" in synonyms["agriculture"]

def test_parse_single_quotes_query():
    """Verifica que el parser soporte comillas simples de forma robusta."""
    q = (
        "(Vision Transformers OR ViT OR 'Transformer models for vision') AND "
        "(CNN OR 'Convolutional Neural Networks') AND "
        "(Agriculture OR 'Precision agriculture' OR 'Agri-tech')"
    )
    concepts, synonyms = _parse_boolean_query_structure(q)
    
    assert "Vision Transformers" in concepts
    assert "ViT" in synonyms["Vision Transformers"]
    assert "Transformer models for vision" in synonyms["Vision Transformers"]
    assert "Convolutional Neural Networks" in synonyms["CNN"]
    assert "Precision agriculture" in synonyms["Agriculture"]

def test_parse_query_with_date_range():
    """Asegura que el filtro de rango de fecha (2020:2026) sea ignorado por el parser de conceptos."""
    q = "(Deep Learning) AND (Agriculture) AND (2020:2026)"
    concepts, _ = _parse_boolean_query_structure(q)
    
    assert "Deep Learning" in concepts
    assert "Agriculture" in concepts
    assert "2020:2026" not in concepts

def test_parse_flat_query_fallback():
    """Valida que si la query no tiene paréntesis, se use el fallback de extracción básica."""
    q = "machine learning AND agriculture AND UAV"
    concepts, _ = _parse_boolean_query_structure(q)
    
    assert "machine learning" in concepts
    assert "agriculture" in concepts
    assert "UAV" in concepts
