import re
import json
import logging
import torch
import numpy as np
from typing import Dict, Any, List, Tuple
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from app.config import settings

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SentimentAnalyzer, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def initialize(self):
        if self.initialized:
            return
        logger.info(f"Loading Sentiment Model: {settings.SENTIMENT_MODEL_NAME}")
        self.tokenizer = AutoTokenizer.from_pretrained(settings.SENTIMENT_MODEL_NAME)
        self.model = AutoModelForSequenceClassification.from_pretrained(settings.SENTIMENT_MODEL_NAME)
        self.model.eval()
        
        # Standardize labels
        # cardiffnlp/twitter-roberta-base-sentiment-latest uses {0: 'negative', 1: 'neutral', 2: 'positive'}
        raw_labels = self.model.config.id2label
        self.label_map = {
            0: "Negative",
            1: "Neutral",
            2: "Positive"
        }
        logger.info(f"Sentiment Model loaded with label map: {self.label_map}")
        self.initialized = True

    def _infer_single_text(self, text: str) -> Tuple[str, float, Dict[str, float]]:
        """Runs the pretrained RoBERTa model on a single string."""
        if not self.initialized:
            self.initialize()

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=256,
            padding=True
        )

        with torch.no_grad():
            outputs = self.model(**inputs)
            probabilities = torch.softmax(outputs.logits, dim=1)[0].cpu().numpy()

        scores = {
            "negative": round(float(probabilities[0]), 4),
            "neutral": round(float(probabilities[1]), 4),
            "positive": round(float(probabilities[2]), 4)
        }

        best_idx = int(np.argmax(probabilities))
        pred_label = self.label_map.get(best_idx, "Neutral")
        confidence = scores[pred_label.lower()]
        return pred_label, confidence, scores

    def _split_clauses(self, text: str) -> List[str]:
        """
        Splits text by contrastive conjunctions and punctuation to identify mixed sentiment.
        Contrasting keywords: but, however, although, though, while, yet, whereas, nevertheless.
        """
        pattern = r'(?:\s*;\s*|\s*,\s*(?:but|however|although|though|while|whereas|yet|nevertheless)\s+|\s+(?:but|however|although|though|while|whereas|yet|nevertheless)\s+)'
        parts = re.split(pattern, text, flags=re.IGNORECASE)
        # Filter out very short segments (under 2 words or 8 characters)
        clauses = [p.strip() for p in parts if len(p.strip().split()) >= 2 and len(p.strip()) >= 8]
        return clauses

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyzes the sentiment of a feedback text with mixed-clause evaluation.
        Requirement:
        - If practical, split the comment into meaningful clauses and run sentiment inference.
        - If one clause is positive and another is negative, classify the overall comment as Neutral (Mixed).
        - Distinguish mixed-result from direct neutral prediction.
        """
        if not self.initialized:
            self.initialize()

        full_label, full_confidence, full_scores = self._infer_single_text(text)

        # Check for mixed sentiment
        clauses = self._split_clauses(text)
        clause_results = []
        has_positive_clause = False
        has_negative_clause = False

        if len(clauses) >= 2:
            for clause in clauses:
                c_label, c_conf, c_scores = self._infer_single_text(clause)
                clause_results.append({
                    "clause": clause,
                    "predicted_label": c_label,
                    "confidence": c_conf,
                    "scores": c_scores
                })
                # Check strong clause sentiment (threshold 0.42 to handle soft praise/critique)
                if c_label == "Positive" and c_scores["positive"] >= 0.42:
                    has_positive_clause = True
                elif c_label == "Negative" and c_scores["negative"] >= 0.42:
                    has_negative_clause = True

        # Mixed sentiment detection
        is_mixed = has_positive_clause and has_negative_clause

        if is_mixed:
            sentiment_label = "Neutral"
            sentiment_detail = "Neutral (Mixed)"
            # Confidence is average of conflicting polarities
            sentiment_confidence = round(float(np.mean([full_scores["positive"], full_scores["negative"]])), 4)
        else:
            sentiment_label = full_label
            sentiment_detail = full_label
            sentiment_confidence = full_confidence

        return {
            "sentiment_label": sentiment_label,
            "sentiment_detail": sentiment_detail,
            "sentiment_confidence": sentiment_confidence,
            "sentiment_scores": full_scores,
            "is_mixed": is_mixed,
            "clause_analysis": clause_results if len(clause_results) >= 2 else None
        }

sentiment_analyzer = SentimentAnalyzer()
