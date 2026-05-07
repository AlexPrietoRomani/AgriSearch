"""
Archivo: active_learning_service.py
Modificación: 2026-05-06
Autor: Alex Prieto

Descripción:
Servicio de Aprendizaje Activo (Active Learning) para asistir en el proceso de cribado.
Utiliza técnicas de procesamiento de lenguaje natural (TF-IDF) y clasificación (Regresión Logística)
para predecir la relevancia de los artículos y priorizar aquellos con mayor incertidumbre o relevancia potencial.

Acciones Principales:
    - Entrena un modelo de clasificación basado en las etiquetas (incluir/excluir) ya asignadas.
    - Predice la probabilidad de relevancia (score) para artículos pendientes.
    - Calcula la incertidumbre de la predicción para implementar "Uncertainty Sampling".
    - Ordena los artículos según diferentes estrategias (relevancia, incertidumbre, balanceado).

Estructura Interna:
    - `ActiveLearningService`: Clase principal que encapsula el pipeline de Scikit-Learn.
    - `_prepare_text`: Limpia y combina campos bibliográficos para vectorización.
    - `train`: Ajusta el modelo a los datos etiquetados.
    - `predict_relevance`: Genera puntuaciones para el pool de artículos.
    - `rank_for_screening`: Reordena la lista según la estrategia seleccionada.

Entradas / Dependencias:
    - Librerías `numpy` y `scikit-learn`.
    - Estados de decisión desde `app.models.project`.

Ejemplo de Integración:
    service = ActiveLearningService()
    service.train(labeled_data)
    ranked_articles = service.predict_relevance(pending_pool)
"""

import logging
from typing import List, Dict, Any, Tuple
import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from app.models.project import ScreeningDecisionStatus

logger = logging.getLogger(__name__)


class ActiveLearningService:
    """
    Servicio que implementa muestreo por incertidumbre (Active Learning) para el cribado bibliográfico.
    """

    def __init__(self):
        """
        Inicializa el vectorizador TF-IDF y el modelo de Regresión Logística balanceada.
        """
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            max_features=5000,
            ngram_range=(1, 2)
        )
        self.model = LogisticRegression(class_weight='balanced', solver='liblinear', random_state=42)
        self._is_trained = False

    def _prepare_text(self, article: Dict[str, Any]) -> str:
        """
        Combina título, abstract y palabras clave en una única cadena para vectorización.

        Args:
            article (Dict[str, Any]): Datos del artículo.

        Returns:
            str: Texto concatenado y normalizado en minúsculas.
        """
        title = article.get('title', '') or ''
        abstract = article.get('abstract', '') or ''
        keywords = article.get('keywords', '') or ''
        
        # Lowercase and basic cleanup
        text = f"{title} {abstract} {keywords}".lower()
        return text

    def train(self, labeled_articles: List[Dict[str, Any]]) -> bool:
        """
        Entrena el clasificador utilizando los artículos que ya tienen una decisión asignada.

        Requiere al menos un ejemplo de cada clase (incluir y excluir) para poder entrenar.

        Args:
            labeled_articles (List[Dict[str, Any]]): Lista de artículos con campo 'decision'.

        Returns:
            bool: True si el entrenamiento fue exitoso, False en caso contrario.
        """
        if not labeled_articles:
            logger.warning("No labeled articles provided for training.")
            return False

        # 1. Filter valid labels and extract text/y
        texts = []
        labels = []
        for a in labeled_articles:
            decision = a.get('decision')
            if decision in [ScreeningDecisionStatus.INCLUDE, ScreeningDecisionStatus.EXCLUDE]:
                texts.append(self._prepare_text(a))
                # Map Include=1, Exclude=0
                labels.append(1 if decision == ScreeningDecisionStatus.INCLUDE else 0)

        # 2. Check if we have enough classes
        if len(set(labels)) < 2:
            logger.info("Not enough diverse samples for training (need at least one include AND one exclude).")
            return False

        # 3. Vectorize and Fit
        try:
            X = self.vectorizer.fit_transform(texts)
            y = np.array(labels)
            self.model.fit(X, y)
            self._is_trained = True
            logger.info(f"Active Learning model trained on {len(labels)} articles.")
            return True
        except Exception as e:
            logger.error(f"Failed to train active learning model: {e}")
            return False

    def predict_relevance(self, pool_articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Predice la probabilidad de inclusión y la incertidumbre para un pool de artículos pendientes.

        Args:
            pool_articles (List[Dict[str, Any]]): Artículos sin decisión tomada.

        Returns:
            List[Dict[str, Any]]: Artículos enriquecidos con 'suggestion_score' e 'uncertainty'.
        """
        if not self._is_trained or not pool_articles:
            return pool_articles

        try:
            texts = [self._prepare_text(a) for a in pool_articles]
            X = self.vectorizer.transform(texts)
            
            # Probability of Class 1 (Include)
            probs = self.model.predict_proba(X)[:, 1]
            
            # Uncertainty = 1 - abs(prob - 0.5) * 2  (0.5 = Max uncertainty, 1.0 = Max certainty)
            # Higher uncertainty is closer to 0.5
            uncertainties = 1 - np.abs(probs - 0.5) * 2

            results = []
            for i, article in enumerate(pool_articles):
                enriched = article.copy()
                enriched['suggestion_score'] = float(probs[i])
                enriched['uncertainty'] = float(uncertainties[i])
                results.append(enriched)
            
            return results

        except Exception as e:
            logger.error(f"Failed to predict relevance: {e}")
            return pool_articles

    @staticmethod
    def rank_for_screening(articles: List[Dict[str, Any]], mode: str = "balanced") -> List[Dict[str, Any]]:
        """
        Ordena los artículos según diferentes estrategias de cribado.

        Estrategias:
            - 'most_relevant': De mayor a menor probabilidad de inclusión.
            - 'uncertainty': De mayor a menor incertidumbre (exploración).
            - 'balanced': Combinación de relevancia e incertidumbre.

        Args:
            articles (List[Dict[str, Any]]): Lista de artículos enriquecidos con puntuaciones.
            mode (str): Modo de ordenamiento.

        Returns:
            List[Dict[str, Any]]: Lista ordenada de artículos.
        """
        if not articles or 'suggestion_score' not in articles[0]:
            return articles

        if mode == "uncertainty":
            # Show the ones where the model is least sure (Active Learning explore)
            return sorted(articles, key=lambda x: x.get('uncertainty', 0), reverse=True)
        elif mode == "most_relevant":
            # Show the most likely to be included (Exploit)
            return sorted(articles, key=lambda x: x.get('suggestion_score', 0), reverse=True)
        else:
            # Balanced: high relevance with high uncertainty
            # Sort by suggested_score * uncertainty? Or weighted sum.
            return sorted(articles, key=lambda x: (x.get('suggestion_score', 0) + x.get('uncertainty', 0)), reverse=True)
