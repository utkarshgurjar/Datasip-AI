"""
DataSip Main Application
FastAPI app entry point: lifespan, CORS, routers, static files.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from backend.database import init_db
from backend.routers import auth, chat, quiz, learning, dashboard
from backend.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("datasip")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifecycle: initialize DB on startup."""
    logger.info("🚀 DataSip starting up...")
    init_db()
    logger.info("✅ Database initialized")
    yield
    logger.info("👋 DataSip shutting down")


# Create FastAPI app
app = FastAPI(
    title="DataSip API",
    description="AI Powered Personalized Learning Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers ───────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(quiz.router)
app.include_router(learning.router)
app.include_router(dashboard.router)

# ── Static Files (Frontend) ───────────────────────────────────────────
# Determine frontend path relative to the project root
_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_frontend_dir = os.path.join(_base_dir, "frontend")

if os.path.isdir(_frontend_dir):
    app.mount("/static", StaticFiles(directory=_frontend_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(os.path.join(_frontend_dir, "index.html"))

    # Catch-all for frontend routes
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        file_path = os.path.join(_frontend_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        # Fallback to index.html for SPA navigation
        return FileResponse(os.path.join(_frontend_dir, "index.html"))
else:
    logger.warning("Frontend directory not found — only API mode active")


@app.get("/api/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": "DataSip", "version": "1.0.0"}
