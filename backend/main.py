"""
main.py
=======
FastAPI application entry point.
Registers middleware, all routers, and global exception handling.

Usage:
    cd backend
    uvicorn main:app --reload --port 8000
"""
from __future__ import annotations
import sys
import os

# Ensure the backend/ directory is on sys.path so that
# `from core.config import ...` works when running from any cwd.
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import get_settings
from routers import rfq, vendors, analysis

settings = get_settings()

# ── Application instance ──────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AI-powered RFQ & Procurement Intelligence Platform. "
        "Supports the full cycle from RFQ creation through vendor evaluation "
        "to multi-scenario award recommendation."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(rfq.router)
app.include_router(vendors.router)
app.include_router(analysis.router)

# ── Health endpoints ──────────────────────────────────────────────────────────

@app.get("/", tags=["Health"], summary="API root")
async def root() -> dict:
    return {
        "app":     settings.app_name,
        "version": settings.app_version,
        "status":  "running",
        "docs":    "/docs",
    }


@app.get("/health", tags=["Health"], summary="Health check")
async def health() -> dict:
    return {"status": "healthy"}


# ── Global exception handler ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "type":   type(exc).__name__,
        },
    )
