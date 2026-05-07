"""
FloodSense AI — District lookup API routes
"""

from fastapi import APIRouter, HTTPException
from ..core.district_service import get_all_districts, get_district

router = APIRouter()


@router.get("/districts", summary="List all supported districts")
async def list_districts():
    return {"districts": get_all_districts()}


@router.get("/districts/{district_id}", summary="Get district details")
async def district_details(district_id: str):
    district = get_district(district_id)
    if district is None:
        raise HTTPException(status_code=404, detail="District not found")
    return {
        "id": district_id.strip().lower(),
        "name": district.name,
        "name_ur": district.name_ur,
        "province": district.province,
        "avg_elevation_m": district.avg_elevation_m,
        "terrain_type": district.terrain_type,
        "terrain_type_ur": district.terrain_type_ur,
        "vulnerability_score": district.vulnerability_score,
        "population_thousands": district.population_thousands,
        "lat": district.lat,
        "lon": district.lon,
        "rivers": district.rivers,
        "flood_history_events": district.flood_history_events,
        "casualties_2022": district.casualties_2022,
        "displaced_2022": district.displaced_2022,
        "ndma_risk_zone": district.ndma_risk_zone,
    }
