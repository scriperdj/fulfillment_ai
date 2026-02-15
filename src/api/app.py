"""FastAPI application — main entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import agents, batch, deviations, health, knowledge, kpi, orders, predict

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: pre-load ML model; Shutdown: cleanup."""
    logger.info("Starting Fulfillment AI API ...")
    try:
        from src.ml.model_loader import load_model, load_preprocessor

        load_model()
        load_preprocessor()
        logger.info("ML model pre-loaded successfully")
    except Exception:
        logger.warning("ML model pre-loading failed — will load on first request", exc_info=True)
    yield
    logger.info("Shutting down Fulfillment AI API")


app = FastAPI(
    title="Fulfillment AI",
    description="AI-driven retail fulfillment risk detection and autonomous resolution",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(predict.router)
app.include_router(batch.router)
app.include_router(deviations.router)
app.include_router(agents.router)
app.include_router(orders.router)
app.include_router(kpi.router)
app.include_router(knowledge.router)


# Global exception handler
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
