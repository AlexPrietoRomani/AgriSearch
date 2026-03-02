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

    Supports:
    - direct dict payloads
    - plain JSON strings
    - JSON wrapped in markdown code fences
    - JSON embedded inside additional text
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

    Uses the configured LLM to produce a structured search strategy
    including boolean query, AGROVOC terms, and PICO breakdown.
    """
    year_filter = ""
    if year_from or year_to:
        year_filter = f"\n- Year range: {year_from or 'any'} to {year_to or 'present'}"

    system_prompt = f"""You are an expert agricultural research librarian specialized in systematic reviews.
Your task is to extract the key research concepts from the user's question and provide synonyms for each.

STRICT DOMAIN ENFORCEMENT:
- THIS SYSTEM IS ONLY FOR AGRICULTURE AND LIFE SCIENCES.
- You MUST filter and EXCLUDE any interpretations related to Social Sciences, Human Medicine (oncology, clinical trials), HVAC, Politics, or Urban Infrastructure UNLESS they are specifically and explicitly linked to agricultural production.
- Example: If the user says "Combate" (Combat), do NOT imply military or social struggle; imply biological control or pest management.
- If keywords are ambiguous, prioritize terms related to: plant pathology, entomology, agronomy, soil science, or crop protection.

CONTEXT:
- Agricultural area: {agri_area}
- User language: {language}
{year_filter}

INSTRUCTIONS:
1. Analyze the user's input and identify 2-5 key research concepts (in English).
2. For EACH concept, provide 1-3 synonyms or closely related terms (in English).
3. Suggest relevant AGROVOC controlled vocabulary terms.
4. Provide a PICO/PEO breakdown if applicable (Population=Crop/Pest, Intervention=Treatment, etc.).
5. Generate a readable summary query combining the main concepts in Boolean logic.

61. CRITICAL: The "concepts" must be SHORT phrases (1-3 words each) in ENGLISH for core compatibility.
62. CRITICAL: For each concept, provide synonyms in BOTH English and Spanish to ensure coverage in regional databases (SciELO/Redalyc).
63. CRITICAL: Do NOT include Boolean operators (AND, OR, NOT, Y, O) or logic expressions inside the concept strings.
64. CRITICAL: The "boolean_query" MUST use English Boolean operators (AND, OR, NOT) exclusively.
65. CRITICAL: If the user's intent is purely non-agricultural, try to map it to the closest agricultural relevance or use agricultural terminology.

RESPOND IN JSON FORMAT:
{{
  "concepts": ["concept1", "concept2", "concept3"],
  "synonyms": {{
    "concept1": ["synonym1a", "synonym1b"],
    "concept2": ["synonym2a"]
  }},
  "boolean_query": "a readable combined query for display (e.g. biological control AND thrips AND strawberry)",
  "suggested_terms": ["agrovoc_term1", "agrovoc_term2"],
  "pico_breakdown": {{
    "population": "description",
    "intervention": "description",
    "comparison": "description",
    "outcome": "description"
  }},
  "explanation": "Brief explanation of the search strategy in {language}"
}}"""

    try:
        requested_model = (model or "").strip()
        llm_model = requested_model or settings.litellm_model
        llm_model_source = "request_payload" if requested_model else "settings_default"

        # Prefix with ollama/ if not present to ensure it routes correctly via LiteLLM
        if not (llm_model.startswith("ollama/") or llm_model.startswith("openai/")):
             llm_model = f"ollama/{llm_model}"

        logger.info(
            "[generate_search_query] model_source=%s requested_model=%r resolved_model=%s api_base=%s",
            llm_model_source,
            requested_model,
            llm_model,
            settings.litellm_api_base,
        )

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

        logger.info("Search query generated successfully for input: %s", user_input[:80])
        return result

    except Exception as e:
        logger.error(
            "LLM query generation failed (requested_model=%r, default_model=%s): %s",
            model,
            settings.litellm_model,
            str(e),
        )

        # Fallback: use the raw input as the query
        return {
            "boolean_query": user_input,
            "suggested_terms": [],
            "pico_breakdown": {},
            "explanation": f"LLM unavailable. Using raw input as query. Error: {str(e)}",
        }


async def translate_text(
    text: str,
    target_language: str = "español",
    model: str = "llama3.1:8b",
) -> str:
    """
    Translate text to the target language using a local LLM.

    The translation is strictly literal — sentence by sentence, preserving
    the exact meaning and structure of the original. No summarization,
    no paraphrasing, no additions.
    """
    system_prompt = f"""You are a professional scientific translator. Your task is to translate the following text to {target_language}.

CRITICAL RULES:
1. Translate LITERALLY, sentence by sentence. Do NOT summarize.
2. Do NOT paraphrase. Preserve the exact meaning and structure of every sentence.
3. Do NOT add explanations, context, or commentary.
4. Do NOT omit any sentence from the original text.
5. Preserve all technical terms, species names (in Latin/italics), chemical names, and numbers exactly.
6. Output ONLY the translated text. No preamble, no notes, no markers.

Translate the following text to {target_language}:"""

    try:
        # Use ollama/ prefix for LiteLLM to route to Ollama
        llm_model = f"ollama/{model}" if not model.startswith("ollama/") else model

        response = await litellm.acompletion(
            model=llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            api_base=settings.litellm_api_base,
            temperature=0.1,  # Low temperature for faithful translation
            max_tokens=4000,
        )

        translated = response.choices[0].message.content.strip()
        logger.info("Translation completed (%d chars → %d chars)", len(text), len(translated))
        return translated


    except Exception as e:
        logger.error("Translation failed: %s", str(e))
        raise


# NOTE: adapt_query_for_database() has been REMOVED.
# Query adaptation is now handled deterministically by app.services.query_builder.
# See query_builder.build_all_queries() for the replacement.


async def generate_relevance_suggestion(
    title: str,
    abstract: str,
    history: list[dict],
    goal: str = "",
    model: str = "aya:8b"
) -> dict:
    """
    Generate an inclusion/exclusion suggestion based on previous decisions (Few-shot learning).
    """
    
    # Format few-shot examples from history
    examples_str = ""
    for i, h in enumerate(history):
        # Clean abstract for prompt
        h_abs = (h['abstract'] or "")[:400].replace("\n", " ")
        examples_str += f"EXAMPLE {i+1}:\nTitle: {h['title']}\nAbstract: {h_abs}...\nDecision: {h['decision'].upper()}\n\n"

    system_prompt = f"""You are a systematic review assistant. Your task is to suggest if a new research article should be INCLUDED or EXCLUDED based on the user's previous decisions and the session goal.

SESSION GOAL: {goal}

PREVIOUS DECISIONS (Context/Style):
{examples_str}

INSTRUCTIONS:
1. Analyze the target article's title and abstract.
2. Based on the patterns in the previous examples and the session goal, decide if it should be included or excluded.
3. Provide a brief justification (1-2 sentences) in Spanish.
4. Output JSON with fields: 'suggested_status' (include/exclude), 'justification' (string), and 'confidence' (float 0.0 to 1.0).

RESPOND IN JSON FORMAT:
{{
  "suggested_status": "include",
  "justification": "Explicación breve en español...",
  "confidence": 0.8
}}"""

    try:
        llm_model = f"ollama/{model}" if not model.startswith("ollama/") else model
        
        response = await litellm.acompletion(
            model=llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"TARGET ARTICLE:\nTitle: {title}\nAbstract: {abstract[:1000]}"},
            ],
            api_base=settings.litellm_api_base,
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=1000,
        )

        content = response.choices[0].message.content
        result = _extract_json_payload(content)
        return result

    except Exception as e:
        logger.error("Relevance suggestion failed: %s", str(e))
        return {
            "suggested_status": "include",
            "justification": "No se pudo generar la sugerencia inteligente.",
            "confidence": 0.0
        }
