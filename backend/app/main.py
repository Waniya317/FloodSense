
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import logging
import uvicorn

from .core.model_service import ModelService
from .api.routes_predict import router as predict_router
from .api.routes_districts import router as districts_router
from .api.routes_simulation import router as simulation_router
from .api.routes_health import router as health_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Singleton model service ────────────────────────────────────────────────────
model_service = ModelService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML artifacts on startup, clean up on shutdown."""
    logger.info(" FloodSense AI starting up...")
    model_service.load()
    logger.info("Models loaded and ready")
    yield
    logger.info(" FloodSense AI shutting down")


# App
app = FastAPI(
    title="FloodSense AI API",
    description="NDMA Pakistan — AI Flood Early Warning System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten to your domain in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Inject model_service into app state so routes can access it ────────────────
app.state.model_service = model_service

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health_router,      prefix="/api/v1", tags=["health"])
app.include_router(predict_router,     prefix="/api/v1", tags=["prediction"])
app.include_router(districts_router,   prefix="/api/v1", tags=["districts"])
app.include_router(simulation_router,  prefix="/api/v1", tags=["simulation"])


@app.get("/")
async def root():
    return {"status": "online", "service": "FloodSense AI", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
