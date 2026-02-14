"""
FastAPI application for fulfillment_ai
Main entry point for REST API
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from src.config import settings


# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    logger.info("🚀 fulfillment_ai starting up...")
    yield
    logger.info("🛑 fulfillment_ai shutting down...")


# Create FastAPI app
app = FastAPI(
    title="fulfillment_ai",
    description="Autonomous AI-driven fulfillment operations system",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.get("/health", tags=["Health"])
async def health_check():
    """System health check"""
    return {
        "status": "healthy",
        "service": "fulfillment_ai",
        "version": "1.0.0",
    }


@app.get("/status", tags=["Health"])
async def status():
    """Detailed system status"""
    return {
        "status": "ready",
        "environment": settings.environment,
        "debug": settings.debug,
        "data_path": settings.data_path,
    }


# ============================================================================
# KPI Endpoints (Placeholder)
# ============================================================================

@app.post("/kpi/compute", tags=["KPI"])
async def compute_kpi():
    """Trigger KPI calculation"""
    logger.info("Computing KPIs...")
    return {
        "message": "KPI computation started",
        "status": "in_progress",
    }


@app.get("/kpi/dashboard", tags=["KPI"])
async def kpi_dashboard():
    """Get current KPI dashboard"""
    return {
        "kpis": {
            "on_time_delivery_rate": 0.0,
            "average_delay_days": 0.0,
            "segment_risk_scores": {},
        },
        "last_updated": None,
    }


# ============================================================================
# Deviation Detection Endpoints (Placeholder)
# ============================================================================

@app.post("/detect-deviation", tags=["Detection"])
async def detect_deviation():
    """Run deviation detection"""
    logger.info("Running deviation detection...")
    return {
        "message": "Deviation detection started",
        "status": "in_progress",
    }


@app.get("/deviations", tags=["Detection"])
async def list_deviations(limit: int = 10, offset: int = 0):
    """List recent deviations"""
    return {
        "deviations": [],
        "total": 0,
        "limit": limit,
        "offset": offset,
    }


# ============================================================================
# Agent Endpoints (Placeholder)
# ============================================================================

@app.post("/trigger-agent", tags=["Agent"])
async def trigger_agent(order_id: str, risk_reason: str = None):
    """Trigger agent on deviation"""
    logger.info(f"Triggering agent for order {order_id}")
    return {
        "message": f"Agent triggered for order {order_id}",
        "status": "in_progress",
    }


@app.get("/agent-response/{response_id}", tags=["Agent"])
async def get_agent_response(response_id: str):
    """Get agent resolution output"""
    return {
        "response_id": response_id,
        "status": "pending",
        "output": None,
    }


# ============================================================================
# Order Endpoints (Placeholder)
# ============================================================================

@app.get("/orders", tags=["Orders"])
async def list_orders(limit: int = 10, offset: int = 0):
    """List orders"""
    return {
        "orders": [],
        "total": 0,
        "limit": limit,
        "offset": offset,
    }


@app.get("/orders/{order_id}", tags=["Orders"])
async def get_order(order_id: str):
    """Get order details"""
    return {
        "order_id": order_id,
        "status": "pending",
        "kpis": {},
    }


# ============================================================================
# Error Handling
# ============================================================================

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return {
        "detail": "Internal server error",
        "error": str(exc) if settings.debug else "Unknown error",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
