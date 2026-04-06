"""
AgriSearch Backend - Summarization Service.

Generates structured "Enriched Summaries" from scientific articles
parsed as Markdown. Focuses on extraction of key evidence.
"""

import logging
from typing import Optional, Dict, Any

import litellm
from app.core.config import get_settings
from app.services.llm_service import _extract_json_payload

logger = logging.getLogger(__name__)
settings = get_settings()

class SummarizationService:
    """
    Service to generate structured summaries from document Markdown.
    """

    SYSTEM_PROMPT = """Eres un analista de revisiones sistemáticas en agricultura.
Tu tarea es leer el contenido de un artículo científico (en Markdown) y generar un resumen ESTRUCTURADO y ENRIQUECIDO en ESPAÑOL.

INSTRUCCIONES:
1. Extrae los puntos clave del estudio.
2. Identifica la metodología específica utilizada.
3. Resume los resultados cuantitativos y cualitativos más importantes.
4. Señala fortalezas y limitaciones críticas del estudio.
5. Proporciona una conclusión concisa alineada con la evidencia.

FORMATO DE SALIDA (JSON):
{
  "objetivo": "Declaración clara del problema y objetivo del estudio.",
  "metodologia": "Descripción breve de materiales, métodos y diseño experimental.",
  "resultados_clave": "Lista de los hallazgos más significativos (incluyendo datos si están disponibles).",
  "limitaciones": "Debilidades o sesgos identificados en el estudio.",
  "conclusiones": "Impacto final o recomendación basada en el estudio.",
  "relevancia_agricola": "Breve nota sobre el impacto práctico para el productor o investigador."
}

IMPORTANTE: 
- El tono debe ser técnico y objetivo.
- Responde ÚNICAMENTE en formato JSON.
"""

    @classmethod
    async def generate_summary(
        cls, 
        md_content: str, 
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calls the LLM to generate a structured summary from Markdown.
        """
        llm_model = model or settings.litellm_model
        if not (llm_model.startswith("ollama/") or llm_model.startswith("openai/")):
            llm_model = f"ollama/{llm_model}"

        # Truncate MD content if too long (max 12k tokens roughly for typical 16k context)
        # Assuming ~4 chars per token for English/Mixed text
        truncated_content = md_content[:40000] 

        try:
            response = await litellm.acompletion(
                model=llm_model,
                messages=[
                    {"role": "system", "content": cls.SYSTEM_PROMPT},
                    {"role": "user", "content": f"DOCUMENTO MARKDOWN:\n\n{truncated_content}"},
                ],
                api_base=settings.litellm_api_base,
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=2000,
            )

            content = response.choices[0].message.content
            summary_data = _extract_json_payload(content)
            
            logger.info("Enriched summary generated successfully.")
            return summary_data

        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return {
                "error": f"No se pudo generar el resumen: {str(e)}",
                "objetivo": "Error en el procesamiento del documento.",
                "metodologia": "N/A",
                "resultados_clave": "N/A",
                "limitaciones": "N/A",
                "conclusiones": "N/A"
            }

    @classmethod
    def format_summary_to_markdown(cls, data: Dict[str, Any]) -> str:
        """Converts the JSON summary data into a clean Markdown string for display."""
        if "error" in data and len(data) == 1:
            return f"**Error:** {data['error']}"

        md = f"### 📄 Resumen Enriquecido\n\n"
        md += f"**🎯 Objetivo:**\n{data.get('objetivo', 'N/A')}\n\n"
        md += f"**🧪 Metodología:**\n{data.get('metodologia', 'N/A')}\n\n"
        md += f"**📊 Resultados Clave:**\n{data.get('resultados_clave', 'N/A')}\n\n"
        md += f"**⚠️ Limitaciones:**\n{data.get('limitaciones', 'N/A')}\n\n"
        md += f"**✅ Conclusiones:**\n{data.get('conclusiones', 'N/A')}\n\n"
        
        relevancia = data.get('relevancia_agricola')
        if relevancia:
            md += f"--- \n> **💡 Relevancia Agrícola:** {relevancia}\n"
            
        return md
