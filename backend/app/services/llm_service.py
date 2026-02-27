"""
AgriSearch Backend - LLM Service.

Thin wrapper around LiteLLM for model-agnostic LLM calls.
Handles query generation, summarization, and all LLM interactions.
"""

import logging
from typing import Any

import litellm

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Configure LiteLLM
litellm.set_verbose = settings.debug


async def generate_search_query(
    user_input: str,
    agri_area: str = "general",
    language: str = "es",
    year_from: int | None = None,
    year_to: int | None = None,
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
Your task is to transform a user's research question into an optimized search strategy.

CONTEXT:
- Agricultural area: {agri_area}
- User language: {language}
{year_filter}

INSTRUCTIONS:
1. Analyze the user's input and identify the key research concepts.
2. Generate a boolean search query using AND, OR, NOT operators.
3. Include synonyms and related terms in English and Spanish.
4. Suggest relevant AGROVOC controlled vocabulary terms.
5. Provide a PICO/PEO breakdown if applicable:
   - P: Population/Problem (e.g., crop, pest, pathogen)
   - I/E: Intervention/Exposure (e.g., treatment, technology)
   - C: Comparison (e.g., control, conventional method)
   - O: Outcome (e.g., yield, efficacy, resistance)

RESPOND IN JSON FORMAT:
{{
  "boolean_query": "the search query with boolean operators",
  "suggested_terms": ["term1", "term2", "term3"],
  "pico_breakdown": {{
    "population": "description",
    "intervention": "description",
    "comparison": "description",
    "outcome": "description"
  }},
  "explanation": "Brief explanation of the search strategy in {language}"
}}"""

    try:
        response = await litellm.acompletion(
            model=settings.litellm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            api_base=settings.litellm_api_base,
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1500,
        )

        import json
        content = response.choices[0].message.content
        result = json.loads(content)

        logger.info("Search query generated successfully for input: %s", user_input[:80])
        return result

    except Exception as e:
        logger.error("LLM query generation failed: %s", str(e))
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


async def adapt_query_for_database(
    boolean_query: str,
    database: str,
) -> str:
    """
    Adapt a general boolean query to the specific syntax constraints of a given scientific database.
    """
    system_prompt = f"""You are an expert scientific database researcher. Your task is to adapt a generic boolean search query into the EXACT specific syntax required by the '{database}' database API.

RULES FOR SPECIFIC DATABASES:
- For 'arxiv': arXiv's API requires field prefixes for every term (e.g., all:term). Replace boolean generalities with proper arXiv API syntax like `all:"term1" AND (all:"term2" OR all:"term3")`.
- For 'openalex': OpenAlex handles standard boolean queries well across its full-text search, but you should ensure quotes are properly escaped or formatted for a URL search parameter. It primarily accepts standard `term1 AND (term2 OR term3)`.
- For 'semantic_scholar': Semantic Scholar's standard query doesn't accept complex nested boolean logic well. Flatten the query or keep only the primary high-value keywords, separating them with spaces or simple ANDs. Skip complex nested ORs if possible.

Given this generic boolean query:
{boolean_query}

Respond ONLY with the transformed query string suitable for '{database}'. Output no other text, no code blocks, no quotes around the output unless it's part of the query."""

    try:
        response = await litellm.acompletion(
            model=settings.litellm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": boolean_query},
            ],
            api_base=settings.litellm_api_base,
            temperature=0.0,
            max_tokens=200,
        )
        adapted = response.choices[0].message.content.strip()
        logger.info("Query adapted for %s: %s -> %s", database, boolean_query, adapted)
        return adapted
    except Exception as e:
        logger.error("Failed to adapt query for %s: %s", database, str(e))
        return boolean_query


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
    import json
    
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
        result = json.loads(content)
        return result

    except Exception as e:
        logger.error("Relevance suggestion failed: %s", str(e))
        return {
            "suggested_status": "include",
            "justification": "No se pudo generar la sugerencia inteligente.",
            "confidence": 0.0
        }
