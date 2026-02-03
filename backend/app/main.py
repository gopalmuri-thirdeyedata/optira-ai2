"""
Optira Document Transformer - FastAPI Application
Main entry point for the backend API.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path
import shutil

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.endpoints import router as api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    settings = get_settings()
    
    # Startup: Create temp directory
    temp_dir = Path(settings.temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    yield
    
    # Shutdown: Clean up temp directory
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        description="Template-based document transformation using AI semantic mapping",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API router
    app.include_router(api_router, prefix="/api", tags=["Document Processing"])
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
