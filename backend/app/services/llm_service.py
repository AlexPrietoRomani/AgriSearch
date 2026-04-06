"""
AgriSearch Backend - LLM Service.

Thin wrapper around LiteLLM for model-agnostic LLM calls.
Handles query generation, summarization, and all LLM interactions.
"""

import logging
import json
from typing import Any

import litellm

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Configure LiteLLM
litellm.set_verbose = settings.debug

def _extract_json_payload(raw_content: Any) -> dict[str, Any]:
    """
    Extract a JSON object from a model response content payload.
    """
    if isinstance(raw_content, dict):
        return raw_content

    if raw_content is None:
        raise ValueError("Empty LLM response content")

    content = str(raw_content).strip()
    if not content:
        raise ValueError("Empty LLM response content")

    # Fast path: direct JSON
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Remove common markdown code fence wrappers
    if content.startswith("```"):
        lines = content.splitlines()
        if len(lines) >= 3 and lines[-1].strip().startswith("```"):
            content = "\n".join(lines[1:-1]).strip()
            if content.lower().startswith("json"):
                content = content[4:].strip()
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass

    # Last resort: extract the first JSON object block found in the text
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and start < end:
        return json.loads(content[start : end + 1])

    raise ValueError("LLM response did not contain valid JSON")

async def generate_search_query(
    user_input: str,
    agri_area: str = "general",
    language: str = "es",
    year_from: int | None = None,
    year_to: int | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Generate an optimized boolean search query from natural language input.
    """
    year_filter = ""
    if year_from or year_to:
        year_filter = f"\n- Year range: {year_from or 'any'} to {year_to or 'present'}"

    system_prompt = f"""You are an expert agricultural research librarian specialized in systematic reviews.
Your task is to extract the key research concepts from the user's question and provide synonyms for each.

CONTEXT:
- Agricultural area: {agri_area}
- User language: {language}
{year_filter}

RESPOND IN JSON FORMAT:
{{
  "concepts": ["concept1", "concept2"],
  "synonyms": {{"concept1": ["syn1"]}},
  "boolean_query": "combined query...",
  "suggested_terms": [],
  "pico_breakdown": {{}},
  "explanation": "..."
}}"""

    try:
        requested_model = (model or "").strip()
        llm_model = requested_model or settings.litellm_model
        if not (llm_model.startswith("ollama/") or llm_model.startswith("openai/")):
             llm_model = f"ollama/{llm_model}"

        response = await litellm.acompletion(
            model=llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            api_base=settings.litellm_api_base,
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1500,
        )

        content = response.choices[0].message.content
        result = _extract_json_payload(content)
        return result
    except Exception as e:
        logger.error("Query generation failed: %s", str(e))
        return {"boolean_query": user_input, "explanation": str(e)}

async def translate_text(
    text: str,
    target_language: str = "español",
    model: str = "llama3.1:8b",
) -> str:
    """Translate text to the target language."""
    system_prompt = f"Translate the following text to {target_language} literally."
    try:
        llm_model = f"ollama/{model}" if not model.startswith("ollama/") else model
        response = await litellm.acompletion(
            model=llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            api_base=settings.litellm_api_base,
            temperature=0.1,
            max_tokens=4000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error("Translation failed: %s", str(e))
        raise

async def generate_relevance_suggestion(
    title: str,
    abstract: str,
    history: list[dict],
    goal: str = "",
    model: str = "gemma4:e4b"
) -> dict:
    """Generate an inclusion/exclusion suggestion based on history."""
    examples_str = ""
    for i, h in enumerate(history):
        h_abs = (h['abstract'] or "")[:400].replace("\n", " ")
        examples_str += f"EXAMPLE {i+1}:\nTitle: {h['title']}\nDecision: {h['decision'].upper()}\n\n"

    system_prompt = f"SESSION GOAL: {goal}\nHISTORY:\n{examples_str}\nDecision in JSON (suggested_status, justification, confidence)."
    try:
        llm_model = f"ollama/{model}" if not model.startswith("ollama/") else model
        response = await litellm.acompletion(
            model=llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Title: {title}\nAbstract: {abstract[:1000]}"},
            ],
            api_base=settings.litellm_api_base,
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=1000,
        )
        return _extract_json_payload(response.choices[0].message.content)
    except Exception as e:
        return {"suggested_status": "include", "justification": str(e), "confidence": 0.0}

async def analyze_article_content(
    md_content: str,
    project_goal: str = "",
    model: str = "gemma4:e4b"
) -> dict[str, Any]:
    """Deep analysis of article content."""
    system_prompt = f"""Analyze this agricultural article. Goal: {project_goal}.
Extract: llm_summary, methodology_type, agri_variables (crops, pests_diseases, chemicals_treatments, environmental_factors), relevance_score, justification.
JSON Format only."""
    try:
        llm_model = f"ollama/{model}" if not model.startswith("ollama/") else model
        content_sample = md_content[:8000]
        response = await litellm.acompletion(
            model=llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content_sample},
            ],
            api_base=settings.litellm_api_base,
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=2000,
        )
        return _extract_json_payload(response.choices[0].message.content)
    except Exception as e:
        return {"llm_summary": str(e), "relevance_score": 0.0}
