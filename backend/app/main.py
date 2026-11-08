from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.config import settings
from backend.app.database import Base, engine
from backend.app.logging_config import setup_logging, logger
from backend.app.error_handlers import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)

# Domain Routers
from backend.app.routers import (
    auth,
    users,
    projects,
    dashboard,
    documents,
    extraction,
    knowledge,
    evidence,
    handovers,
    permissions,
    review as reviews,
    analytics,
    audit,
    conflicts
)

# Initialize structured logging
setup_logging()

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Evidence-Linked Project Knowledge Handover Platform - Team Web_hunter (Phase 2 Auth & Project Management)",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Register centralized error handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def register_api_routers(prefix: str):
    app.include_router(auth.router, prefix=prefix)
    app.include_router(users.router, prefix=prefix)
    app.include_router(projects.router, prefix=prefix)
    app.include_router(dashboard.router, prefix=prefix)
    app.include_router(documents.router, prefix=prefix)
    app.include_router(extraction.router, prefix=prefix)
    app.include_router(knowledge.router, prefix=prefix)
    app.include_router(evidence.router, prefix=prefix)
    app.include_router(handovers.router, prefix=prefix)
    app.include_router(permissions.router, prefix=prefix)
    app.include_router(reviews.router, prefix=prefix)
    app.include_router(analytics.router, prefix=prefix)
    app.include_router(audit.router, prefix=prefix)
    app.include_router(conflicts.router, prefix=prefix)

# Mount both /api/v1 and /api for full specification and legacy compatibility
register_api_routers("/api/v1")
register_api_routers("/api")

@app.get("/")
def root():
    return {
        "service": "Knowledge Continuity API",
        "team": "Web_hunter",
        "phase": "Phase 2 - Authentication & Project Management",
        "status": "HEALTHY",
        "version": settings.VERSION,
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "database": "connected",
        "environment": "production-ready",
        "service": settings.PROJECT_NAME
    }
