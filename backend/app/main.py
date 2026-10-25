
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routes import health, instructors, feedback, analytics, departments
from app.routes import auth
from app.routes.auth import verify_session_token
from app.routes.departments import ensure_initial_departments
from app.nlp.sentiment import sentiment_analyzer
from app.nlp.topic_clustering import topic_clusterer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app.main")

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
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
        logger.info("NLP models initialized.")
    except Exception:
        logger.exception("Failed to initialize NLP models.")

    yield
    logger.info("Shutting down application...")


app = FastAPI(
    title="StuFeed - Student Feedback Intelligence Platform",
    description="Backend API for student feedback topic intelligence and sentiment analysis",
    version="1.0.0",
    lifespan=lifespan,
)

# Restrict browser origins to the local frontend by default.
# Set STUFEED_FRONTEND_ORIGINS to a comma-separated allowlist if needed.
frontend_origins = [
    item.strip()
    for item in os.getenv(
        "STUFEED_FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if item.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


def _requires_admin(request: Request) -> bool:
    path = request.url.path
    method = request.method.upper()

    # Analytics and department overview contain admin-only insights.
    if path.startswith("/api/analytics/"):
        return True

    if path == "/api/departments/overview":
        return True

    # Viewing all feedback is admin-only. Student submission stays public.
    if path == "/api/feedback" and method == "GET":
        return True

    # Department mutations require an authenticated administrator.
    if path == "/api/departments" and method in {"POST", "PUT", "DELETE"}:
        return True
    if path.startswith("/api/departments/") and method in {"POST", "PUT", "DELETE"}:
        return True

    # Subject and instructor writes require an administrator.
    if path.startswith("/api/subjects") and method in {"POST", "PUT", "DELETE"}:
        return True
    if path.startswith("/api/instructors") and method in {"POST", "PUT", "DELETE"}:
        return True

    # include_inactive exposes records used by academic management.
    if path in {"/api/subjects", "/api/instructors"}:
        if request.query_params.get("include_inactive", "false").lower() == "true":
            return True

    return False


@app.middleware("http")
async def enforce_admin_authentication(request: Request, call_next):
    # Public login, health checks, and CORS preflight requests.
    if (
        request.method == "OPTIONS"
        or request.url.path in {"/api/auth/login", "/api/health", "/"}
    ):
        return await call_next(request)

    if not _requires_admin(request):
        return await call_next(request)

    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token or not verify_session_token(token):
        return JSONResponse(
            status_code=401,
            content={"detail": "Admin login required or session expired."},
        )

    return await call_next(request)


app.include_router(health.router)
app.include_router(auth.router)
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
        "health": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
