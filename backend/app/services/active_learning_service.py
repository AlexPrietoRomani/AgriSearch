"""
AgriSearch Backend - Active Learning Service.

Implements screening assistance using simple ML (TF-IDF + Logistic Regression)
to re-rank articles by uncertainty or potential relevance.
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
    Implements simple active learning (Uncertainty Sampling) for screening.
    """

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            max_features=5000,
            ngram_range=(1, 2)
        )
        self.model = LogisticRegression(class_weight='balanced', solver='liblinear', random_state=42)
        self._is_trained = False

    def _prepare_text(self, article: Dict[str, Any]) -> str:
        """Combines title, abstract, and keywords for vectorization."""
        title = article.get('title', '') or ''
        abstract = article.get('abstract', '') or ''
        keywords = article.get('keywords', '') or ''
        
        # Lowercase and basic cleanup
        text = f"{title} {abstract} {keywords}".lower()
        return text

    def train(self, labeled_articles: List[Dict[str, Any]]) -> bool:
        """
        Trains the classifier on already labeled articles (included/excluded).
        
        labeled_articles: List of dicts with keys 'title', 'abstract', 'keywords', 'decision'
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
        Predicts inclusion probability and uncertainty for a pool of pending articles.
        Returns the article list with added 'suggestion_score' and 'uncertainty'.
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
        Ranks articles according to different strategies:
        - 'most_relevant': Descending by suggestion_score.
        - 'uncertainty': Descending by uncertainty (most unsure first).
        - 'balanced': Combination (e.g., top relevance first, then high uncertainty).
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
