import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routes import health, instructors, feedback, analytics, departments
from app.routes.departments import ensure_initial_departments
from app.nlp.sentiment import sentiment_analyzer
from app.nlp.topic_clustering import topic_clusterer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("app.main")

# Ensure database tables exist
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure initial departments & load models
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        ensure_initial_departments(db)
    finally:
        db.close()

    logger.info("Initializing NLP models on server startup...")
    try:
        sentiment_analyzer.initialize()
        topic_clusterer.initialize()
        logger.info("NLP models successfully initialized and ready for inference.")
    except Exception as e:
        logger.error(f"Failed to initialize NLP models during startup: {e}")
    yield
    # Shutdown
    logger.info("Shutting down application...")

app = FastAPI(
    title="StuFeed - Student Feedback Intelligence Platform",
    description="Backend API for Student Feedback Topic Intelligence & Sentiment Analysis",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(health.router)
app.include_router(departments.router)
app.include_router(instructors.router)
app.include_router(feedback.router)
app.include_router(analytics.router)

@app.get("/")
def root():
    return {
        "title": settings.APP_NAME,
        "status": "online",
        "documentation": "/docs",
        "health": "/api/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
