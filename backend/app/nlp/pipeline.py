import json
import logging
from typing import List, Dict, Any
from app.nlp.sentiment import sentiment_analyzer
from app.nlp.topic_clustering import topic_clusterer

logger = logging.getLogger(__name__)

def process_single_feedback(text: str) -> Dict[str, Any]:
    """
    Runs sentiment analysis on a new feedback submission.
    """
    return sentiment_analyzer.analyze(text)

def compute_topic_clusters(submissions: List[Any]) -> List[Dict[str, Any]]:
    """
    Computes topic clusters on a list of feedback records.
    Each item can be an ORM object or dictionary.
    """
    formatted_data = []
    for s in submissions:
        if hasattr(s, "feedback_text"):
            # ORM object
            scores = {}
            if s.sentiment_scores:
                try:
                    scores = json.loads(s.sentiment_scores)
                except Exception:
                    scores = {}
            formatted_data.append({
                "id": s.id,
                "department_name": getattr(s, "department_name", "Other"),
                "is_other": getattr(s, "is_other", False),
                "subject_name": s.subject_name,
                "instructor_name": s.instructor_name,
                "rating": s.rating,
                "feedback_text": s.feedback_text,
                "sentiment_label": s.sentiment_label,
                "sentiment_detail": s.sentiment_detail,
                "sentiment_confidence": s.sentiment_confidence,
                "sentiment_scores": scores,
                "is_mixed": s.is_mixed,
                "cluster_id": s.cluster_id,
                "topic_label": s.topic_label,
                "created_at": s.created_at
            })
        else:
            formatted_data.append(s)

    return topic_clusterer.cluster_feedback(formatted_data)
