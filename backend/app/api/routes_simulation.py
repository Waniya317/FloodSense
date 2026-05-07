"""
FloodSense AI — Simulation API routes
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/simulation", summary="Simulation status")
async def simulation_status():
    return {
        "status": "ready",
        "message": "Simulation endpoint is available",
    }
