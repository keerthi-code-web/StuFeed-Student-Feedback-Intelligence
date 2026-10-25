from fastapi import APIRouter
from app.nlp.sentiment import sentiment_analyzer
from app.nlp.topic_clustering import topic_clusterer
from app.config import settings

router = APIRouter(prefix="/api/health", tags=["Health"])

@router.get("")
def health_check():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "models": {
            "sentiment": {
                "name": settings.SENTIMENT_MODEL_NAME,
                "loaded": sentiment_analyzer.initialized
            },
            "embedding": {
                "name": settings.EMBEDDING_MODEL_NAME,
                "loaded": topic_clusterer.initialized
            }
        }
    }
