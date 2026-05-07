"""
Archivo: llm_service.py
Modificación: 2026-05-06
Autor: Alex Prieto

Descripción:
Capa de abstracción para interacciones con Modelos de Lenguaje (LLM).
Utiliza LiteLLM para proporcionar una interfaz agnóstica al proveedor (OpenAI, Ollama, etc.).
Gestiona la generación de consultas, resúmenes, análisis de relevancia y visión artificial.

Acciones Principales:
    - Generación de consultas booleanas optimizadas a partir de lenguaje natural.
    - Traducción técnica de términos y abstracts.
    - Análisis profundo de artículos científicos (extracción de variables agrícolas).
    - Descripción de imágenes y diagramas mediante modelos de visión (VLM).
    - Sugerencias inteligentes de inclusión/exclusión para el cribado.

Estructura Interna:
    - `_extract_json_payload`: Utilidad robusta para extraer JSON de respuestas de texto.
    - `generate_search_query`: Genera lógica booleana y desglose PICO.
    - `analyze_article_content`: Extrae variables específicas (cultivos, plagas, tratamientos).
    - `describe_image_content`: Genera descripciones y código Mermaid para figuras.

Entradas / Dependencias:
    - Librería `litellm`.
    - Servidor Ollama local o API de OpenAI según configuración en `Settings`.

Ejemplo de Integración:
    query_data = await generate_search_query("impacto del glifosato en maíz")
"""

import logging
import json
from typing import Any

import litellm

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Configurar LiteLLM
litellm.set_verbose = settings.debug


def _extract_json_payload(raw_content: Any) -> dict[str, Any]:
    """
    Extrae de forma robusta un objeto JSON del contenido de la respuesta del modelo.

    Maneja bloques de código Markdown (```json ... ```) y texto plano.

    Args:
        raw_content (Any): Contenido crudo retornado por el LLM.

    Returns:
        dict[str, Any]: Objeto JSON parseado.

    Raises:
        ValueError: Si no se encuentra un JSON válido en la respuesta.
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
    Genera una consulta de búsqueda booleana optimizada a partir de una entrada en lenguaje natural.

    Args:
        user_input (str): Pregunta o tema de investigación del usuario.
        agri_area (str): Área agrícola específica para contextualizar términos.
        language (str): Idioma de la consulta original.
        year_from (int | None): Filtro de año inicial.
        year_to (int | None): Filtro de año final.
        model (str | None): Modelo específico a utilizar (opcional).

    Returns:
        dict[str, Any]: Diccionario con la consulta booleana, sinónimos y desglose PICO.
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
    """
    Traduce texto al idioma objetivo manteniendo el tono técnico.

    Args:
        text (str): Texto a traducir.
        target_language (str): Idioma de destino.
        model (str): Modelo a utilizar.

    Returns:
        str: Texto traducido.
    """
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
    """
    Genera una sugerencia de inclusión/exclusión basada en el historial previo de cribado.

    Implementa aprendizaje en pocos pasos (few-shot) para guiar al usuario.

    Args:
        title (str): Título del artículo a evaluar.
        abstract (str): Resumen del artículo.
        history (list[dict]): Lista de decisiones previas tomadas por el usuario.
        goal (str): Objetivo general de la revisión sistemática.
        model (str): Modelo a utilizar.

    Returns:
        dict: Sugerencia con estado, justificación y nivel de confianza.
    """
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
    """
    Realiza un análisis profundo del contenido de un artículo (Markdown) para extraer variables agrícolas.

    Args:
        md_content (str): Texto completo del artículo en Markdown.
        project_goal (str): Objetivo del proyecto para orientar la relevancia.
        model (str): Modelo a utilizar (se recomienda uno con ventana de contexto amplia).

    Returns:
        dict[str, Any]: Diccionario con resumen, score de relevancia y variables extraídas.
    """
    system_prompt = f"""Analyze this agricultural article content. Goal: {project_goal}.
Extract: llm_summary, methodology_type, agri_variables (crops, pests_diseases, chemicals_treatments, environmental_factors), relevance_score, justification.
JSON Format only."""
    try:
        requested_model = model or settings.litellm_model
        llm_model = requested_model if requested_model.startswith("ollama/") else f"ollama/{requested_model}"
        content_sample = md_content[:15000] # Gemma 4 has larger context window
        response = await litellm.acompletion(
            model=llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content_sample},
            ],
            api_base=settings.litellm_api_base,
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=2500,
        )
        return _extract_json_payload(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Deep analysis failed: {e}")
        return {"llm_summary": str(e), "relevance_score": 0.0}


async def describe_image_content(
    image_base64: str,
    context: str = "",
    model: str = "gemma4:e4b"
) -> str:
    """
    Utiliza un modelo de visión (VLM) para describir imágenes o diagramas de artículos científicos.

    Args:
        image_base64 (str): Imagen codificada en base64.
        context (str): Contexto textual (ej: título del artículo) para guiar la descripción.
        model (str): Modelo de visión a utilizar.

    Returns:
        str: Descripción técnica de la imagen.
    """
    system_prompt = f"""You are a scientific vision assistant.
Describe the provided image or diagram from a research paper.
If it is a workflow or chart, try to describe the logic concisely.
If appropriate, provide a Mermaid diagram code block.
Focus: Agricultural context if applicable ({context})."""
    
    try:
        requested_model = model or settings.litellm_model
        llm_model = requested_model if requested_model.startswith("ollama/") else f"ollama/{requested_model}"
        
        response = await litellm.acompletion(
            model=llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this figure:"},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                        }
                    ]
                }
            ],
            api_base=settings.litellm_api_base,
            temperature=0.2,
            max_tokens=1500,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Image description failed: {e}")
        return f"[Image description failed: {e}]"
