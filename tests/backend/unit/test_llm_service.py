"""Unit tests for robust LLM JSON response parsing."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

import pytest

from app.services.llm_service import _extract_json_payload


def test_extract_json_payload_with_plain_json():
    payload = '{"boolean_query": "rust AND blueberry", "explanation": "ok"}'

    result = _extract_json_payload(payload)

    assert result["boolean_query"] == "rust AND blueberry"
    assert result["explanation"] == "ok"


def test_extract_json_payload_with_markdown_fence():
    payload = """```json
{
  "boolean_query": "blueberry AND fungicide",
  "suggested_terms": ["blueberries"]
}
```"""

    result = _extract_json_payload(payload)

    assert result["boolean_query"] == "blueberry AND fungicide"
    assert result["suggested_terms"] == ["blueberries"]


def test_extract_json_payload_embedded_in_text():
    payload = (
        "Aquí tienes la estrategia:\n"
        "{\"boolean_query\": \"crop AND rust\", \"explanation\": \"estrategia\"}\n"
        "Espero que sirva"
    )

    result = _extract_json_payload(payload)

    assert result["boolean_query"] == "crop AND rust"
    assert result["explanation"] == "estrategia"


def test_extract_json_payload_dict_passthrough():
    payload = {"boolean_query": "a AND b", "explanation": "ok"}

    result = _extract_json_payload(payload)

    assert result is payload


def test_extract_json_payload_invalid_raises():
    with pytest.raises(ValueError):
        _extract_json_payload("sin json")
