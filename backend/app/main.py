"""BIND Backend Application - FastAPI Entry Point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("=" * 60)
    logger.info("BIND Kernel starting up...")
    logger.info(f"  Mock mode: {settings.use_mocks}")
    logger.info(f"  AWS Region: {settings.aws_region}")
    logger.info(f"  Planner Model: {settings.planner_model_id}")
    logger.info(f"  Teacher Vision: {settings.teacher_vision_model_id}")
    logger.info(f"  Student Vision: {settings.student_vision_model_id}")
    logger.info(f"  Max Docket Cost: ${settings.max_docket_cost_usd}")
    logger.info(f"  Confidence Threshold: {settings.student_confidence_threshold}")
    logger.info("=" * 60)
    yield
    logger.info("BIND Kernel shutting down.")


app = FastAPI(
    title="BIND - Cross-Modal Claim Runtime",
    description="Parcel-level crop intelligence docket API for FarmwiseAI Task 1.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS (allow frontend to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
