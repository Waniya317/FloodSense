"""
FloodSense AI — Health check API routes
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Health check")
async def health_check():
    return {"status": "ok", "service": "FloodSense AI"}
