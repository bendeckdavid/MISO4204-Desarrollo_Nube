"""
FastAPI application

Main entry point for the API.
Register your routers here.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes import auth, health, videos, public
from app.core.config import settings
from app.db.base import Base
from app.db.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover
    """Lifecycle events"""
    with engine.connect() as conn:
        try:
            conn.execute(text("SELECT pg_advisory_lock(123456789)"))
            from app.db import models  # noqa: F401

            Base.metadata.create_all(bind=engine, checkfirst=True)
        finally:
            conn.execute(text("SELECT pg_advisory_unlock(123456789)"))
            conn.commit()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    description="FastAPI Template - Scalable REST API with async processing",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(videos.router, prefix=f"{settings.API_V1_STR}/videos", tags=["Videos"])
app.include_router(public.router, prefix=f"{settings.API_V1_STR}/public", tags=["Publicacion"])
