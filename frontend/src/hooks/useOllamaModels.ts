/**
 * Hook React para obtener modelos Ollama dinámicamente desde el backend.
 * Elimina las listas hardcodeadas de modelos en los componentes.
 */

import { useState, useEffect, useMemo } from 'react';
import { getOllamaModels, type OllamaModel } from '../lib/api';

interface UseOllamaModelsReturn {
  models: OllamaModel[];
  recommendedModel: string;
  loading: boolean;
  error: string | null;
}

export function useOllamaModels(): UseOllamaModelsReturn {
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    getOllamaModels()
      .then((data) => {
        if (!cancelled) {
          const nonEmbedding = data.filter((m) => !m.is_embedding);
          setModels(nonEmbedding);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message || 'Ollama no disponible');
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, []);

  const recommendedModel = useMemo(() => {
    if (models.length === 0) return '';
    const multimodal = models.find((m) => m.is_multimodal);
    if (multimodal) return multimodal.name;
    const knownGood = models.find((m) =>
      m.name.includes('qwen') || m.name.includes('deepseek') || m.name.includes('phi')
    );
    if (knownGood) return knownGood.name;
    return models[0]?.name || '';
  }, [models]);

  return { models, recommendedModel, loading, error };
}
