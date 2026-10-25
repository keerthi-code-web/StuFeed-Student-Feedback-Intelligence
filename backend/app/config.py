import os
from pathlib import Path
from pydantic import BaseModel

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BACKEND_DIR / "feedback.db"

class Settings(BaseModel):
    APP_NAME: str = "StuFeed - Student Feedback Intelligence Platform"
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH.as_posix()}")
    SENTIMENT_MODEL_NAME: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    CLUSTERING_DISTANCE_THRESHOLD: float = 0.65
    MIN_TOPIC_SIZE: int = 1

settings = Settings()
