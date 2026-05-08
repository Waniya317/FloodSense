"""
FloodSense AI — Prediction API Routes
POST /api/v1/predict — Main flood risk prediction endpoint
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Optional
import numpy as np
import math
import logging
from dataclasses import asdict

from ..core.recommendation_engine import build_recommendation
from ..core.district_service import get_district, get_elevation_lookup

logger = logging.getLogger(__name__)
router = APIRouter()


def clean_nan(obj):
    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan(v) for v in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return 0.0
    return obj


# ── Request Schema ─────────────────────────────────────────────────────────────
class PredictRequest(BaseModel):
    district: str = Field(..., min_length=2, max_length=60, example="buner")
    date: Optional[str] = Field(None, example="2025-08-15")

    # Weather inputs (all optional — missing values are imputed)
    precipitation: Optional[float] = Field(None, ge=0, le=3000, example=78.5)
    temperature: Optional[float] = Field(None, ge=-20, le=60, example=28.3)
    humidity: Optional[float] = Field(None, ge=0, le=100, example=82.0)
    wind_speed: Optional[float] = Field(None, ge=0, le=60, example=12.0)
    pressure: Optional[float] = Field(None, ge=80000, le=110000, example=98500.0)
    soil_moisture: Optional[float] = Field(None, ge=0, le=1, example=0.72)
    evaporation: Optional[float] = Field(None, ge=0, le=50, example=4.2)
    water_area_km2: Optional[float] = Field(None, ge=0, example=12.3)
    water_area_pct_change: Optional[float] = Field(None, ge=-500, le=500, example=45.2)

    # Rolling features
    precip_3day_avg: Optional[float] = Field(None, ge=0, le=3000)
    precip_7day_avg: Optional[float] = Field(None, ge=0, le=3000)
    temp_3day_avg: Optional[float] = Field(None, ge=-20, le=60)
    soil_3day_avg: Optional[float] = Field(None, ge=0, le=1)
    water_area_change: Optional[float] = Field(None)

    # Temporal
    day_of_year: Optional[int] = Field(None, ge=1, le=366)
    month: Optional[int] = Field(None, ge=1, le=12)
    year: Optional[int] = Field(None, ge=2000, le=2100)
    is_monsoon: Optional[int] = Field(None, ge=0, le=1)

    @validator("district")
    def clean_district(cls, v):
        return v.strip().lower()

    class Config:
        json_schema_extra = {
            "example": {
                "district": "buner",
                "precipitation": 78.5,
                "temperature": 28.3,
                "humidity": 82.0,
                "wind_speed": 12.0,
                "soil_moisture": 0.72,
                "month": 8,
                "is_monsoon": 1,
            }
        }


# ── Feature Vector Builder ─────────────────────────────────────────────────────
def build_feature_vector(req: PredictRequest, feature_names: list, elevation_lookup: dict) -> np.ndarray:
    """
    Convert validated request into a feature vector aligned with model's feature_names.
    Handles missing values gracefully with sensible defaults.
    """
    # Derive temporal features if date is provided
    month = req.month
    day_of_year = req.day_of_year
    year = req.year
    is_monsoon = req.is_monsoon

    if req.date:
        try:
            from datetime import date as ddate
            d = ddate.fromisoformat(req.date)
            month = month or d.month
            day_of_year = day_of_year or d.timetuple().tm_yday
            year = year or d.year
        except Exception:
            pass

    if month is not None and is_monsoon is None:
        is_monsoon = 1 if month in (6, 7, 8, 9) else 0

    # Get elevation from lookup
    elevation = elevation_lookup.get(req.district, 500.0)

    # Build raw dict with defaults and derived inputs.
    raw = {
        "elevation": elevation,
        "evaporation": req.evaporation if req.evaporation is not None else 4.0,
        "latitude": 33.0,   # rough Pakistan center; will be overridden by district info
        "longitude": 71.0,
        "precipitation": req.precipitation if req.precipitation is not None else 0.0,
        "pressure": req.pressure if req.pressure is not None else 100000.0,
        "soil_moisture": req.soil_moisture if req.soil_moisture is not None else 0.4,
        "temperature": req.temperature if req.temperature is not None else 25.0,
        "water_area_km2": req.water_area_km2 if req.water_area_km2 is not None else 5.0,
        "wind_speed": req.wind_speed if req.wind_speed is not None else 8.0,
        "humidity": req.humidity if req.humidity is not None else 60.0,
        "precip_3day_avg": req.precip_3day_avg if req.precip_3day_avg is not None else (req.precipitation or 0.0),
        "precip_7day_avg": req.precip_7day_avg if req.precip_7day_avg is not None else (req.precipitation or 0.0),
        "temp_3day_avg": req.temp_3day_avg if req.temp_3day_avg is not None else (req.temperature if req.temperature is not None else 25.0),
        "soil_3day_avg": req.soil_3day_avg if req.soil_3day_avg is not None else (req.soil_moisture if req.soil_moisture is not None else 0.4),
        "water_area_change": req.water_area_change if req.water_area_change is not None else 0.0,
        "water_area_pct_change": req.water_area_pct_change if req.water_area_pct_change is not None else 0.0,
        "day_of_year": day_of_year or 200,
        "month": month or 8,
        "year": year or 2025,
        "is_monsoon": is_monsoon if is_monsoon is not None else 0,
    }

    # Get district lat/lon and terrain
    district_info = get_district(req.district)
    terrain_type = "unknown"
    if district_info:
        raw["latitude"] = district_info.lat
        raw["longitude"] = district_info.lon
        terrain_type = district_info.terrain_type or terrain_type

    # Amplify core flood signals so the model responds more strongly to extreme weather.
    raw["precipitation"] = min(raw["precipitation"] * 2.5, 3000.0)
    raw["wind_speed"] = min(raw["wind_speed"] * 2.0, 60.0)
    raw["soil_moisture"] = min(raw["soil_moisture"] * 2.0, 1.0)
    raw["humidity"] = min(raw["humidity"] * 1.2, 100.0)
    raw["water_area_km2"] = min(raw["water_area_km2"] * 1.5, 1000.0)

    # Derive engineered features like training pipeline.
    raw["water_area_pct_change"] = float(np.clip(raw["water_area_pct_change"], -500.0, 500.0))
    raw["flood_stress_index"] = (
        raw["precip_7day_avg"] * 0.4
        + raw["soil_moisture"] * 0.3
        + max(0.0, raw["water_area_pct_change"]) / 500.0 * 0.3
    )
    raw["sat_proxy"] = raw["soil_moisture"] * raw["precip_3day_avg"]
    raw["monsoon_precip"] = raw["is_monsoon"] * raw["precipitation"]
    raw["heat_index"] = raw["temperature"] + 0.33 * raw["humidity"] - 4.0

    elevation_scale = 2000.0
    raw["elevation_risk"] = 1.0 - min(raw["elevation"] / elevation_scale, 1.0)

    if raw["day_of_year"] is None:
        raw["day_of_year"] = 200
    if raw["month"] is None:
        raw["month"] = 8
    raw["doy_sin"] = np.sin(2 * np.pi * float(raw["day_of_year"]) / 365)
    raw["doy_cos"] = np.cos(2 * np.pi * float(raw["day_of_year"]) / 365)
    raw["month_sin"] = np.sin(2 * np.pi * float(raw["month"]) / 12)
    raw["month_cos"] = np.cos(2 * np.pi * float(raw["month"]) / 12)

    # Build vector in feature_names order, filling zeros for unknown features.
    vec = []
    district_key = req.district.strip().lower()
    terrain_key = str(terrain_type).strip().lower()
    for fname in feature_names:
        if fname.startswith("district_"):
            vec.append(1.0 if fname.lower() == f"district_{district_key}" else 0.0)
            continue
        if fname.startswith("terrain_type_"):
            vec.append(1.0 if fname.lower() == f"terrain_type_{terrain_key}" else 0.0)
            continue
        if fname == "elevation_merged" or fname == "avg_elevation_m":
            val = raw.get("elevation", raw.get("avg_elevation_m", 0.0))
        else:
            val = raw.get(fname, 0.0)
        if val is None or (isinstance(val, float) and np.isnan(val)):
            val = 0.0
        vec.append(float(val))

    return np.array(vec, dtype=np.float32).reshape(1, -1)


# ── Friendly Feature Labels ────────────────────────────────────────────────────
FEATURE_LABELS = {
    "precipitation": "Rainfall",
    "precip_7day_avg": "7-Day Avg Rainfall",
    "precip_3day_avg": "3-Day Avg Rainfall",
    "soil_moisture": "Soil Moisture",
    "water_area_pct_change": "Water Area Change",
    "water_area_change": "Water Area Change (km²)",
    "elevation": "Elevation",
    "humidity": "Humidity",
    "is_monsoon": "Monsoon Season",
    "temperature": "Temperature",
    "wind_speed": "Wind Speed",
    "pressure": "Atmospheric Pressure",
    "evaporation": "Evaporation Rate",
    "flood_stress_index": "Flood Stress Index",
    "elevation_risk": "Elevation Risk Factor",
    "sat_proxy": "Soil Saturation",
    "monsoon_precip": "Monsoon Precipitation",
    "heat_index": "Heat Index",
}

FEATURE_LABELS_UR = {
    "precipitation": "بارش",
    "precip_7day_avg": "7 دن کی اوسط بارش",
    "precip_3day_avg": "3 دن کی اوسط بارش",
    "soil_moisture": "مٹی کی نمی",
    "water_area_pct_change": "پانی کی سطح میں تبدیلی",
    "elevation": "بلندی",
    "humidity": "نمی",
    "is_monsoon": "مون سون موسم",
    "temperature": "درجہ حرارت",
    "wind_speed": "ہوا کی رفتار",
    "flood_stress_index": "سیلاب تناؤ اشاریہ",
    "elevation_risk": "بلندی خطرہ عنصر",
}


def _input_severity_score(req: PredictRequest) -> float:
    """Compute a lightweight severity score from strong flood signals."""
    score = 0.0

    if req.precipitation is not None:
        score += min(req.precipitation / 220.0, 1.0) * 0.42
    if req.humidity is not None:
        score += min(req.humidity / 100.0, 1.0) * 0.19
    if req.soil_moisture is not None:
        score += min(req.soil_moisture / 1.0, 1.0) * 0.19
    if req.wind_speed is not None:
        score += min(req.wind_speed / 40.0, 1.0) * 0.10
    if req.water_area_km2 is not None:
        score += min(req.water_area_km2 / 50.0, 1.0) * 0.05
    if req.is_monsoon == 1:
        score += 0.05
    if req.month in (6, 7, 8, 9):
        score += 0.05

    return min(score, 1.0)


def _override_probability_by_input(req: PredictRequest, probability: float) -> float:
    """Use strong input signals to align final probability with extreme flood conditions."""
    severity = _input_severity_score(req)
    if severity >= 0.80:
        return max(probability, 0.95)
    if severity >= 0.70:
        return max(probability, 0.85)
    if severity >= 0.60:
        return max(probability, 0.70)
    if severity >= 0.50:
        return max(probability, 0.60)
    if severity >= 0.40:
        return max(probability, 0.45)
    if severity >= 0.25:
        return max(probability, 0.25)
    return probability


def humanize_explanation(explanations: list[dict], feature_names: list) -> list[dict]:
    """Convert raw SHAP output to human-readable, non-technical explanations."""
    readable = []
    for exp in explanations:
        fname = exp["feature"]
        label = FEATURE_LABELS.get(fname, fname.replace("_", " ").title())
        label_ur = FEATURE_LABELS_UR.get(fname, label)
        val = exp["value"]
        direction = exp["direction"]
        impact_pct = min(abs(exp["impact"]) * 100, 99)

        # Human-readable value
        if fname == "precipitation":
            val_str = f"{val:.1f} mm"
        elif fname == "soil_moisture":
            val_str = f"{val*100:.0f}%"
        elif fname == "humidity":
            val_str = f"{val:.0f}%"
        elif fname == "elevation":
            val_str = f"{val:.0f} m"
        elif fname == "temperature":
            val_str = f"{val:.1f}°C"
        elif fname == "wind_speed":
            val_str = f"{val:.1f} m/s"
        elif fname in ("is_monsoon",):
            val_str = "Yes" if val > 0.5 else "No"
        else:
            val_str = f"{val:.2f}"

        readable.append({
            "feature": fname,
            "label": label,
            "label_ur": label_ur,
            "value": val_str,
            "impact": round(exp["impact"], 4),
            "impact_pct": round(impact_pct, 1),
            "direction": direction,
        })
    return readable


# ── Route ─────────────────────────────────────────────────────────────────────
@router.post("/predict")
async def predict(request: Request, body: PredictRequest):
    model_service = request.app.state.model_service

    if not model_service.is_ready:
        raise HTTPException(503, detail="Model service not initialized")

    elevation_lookup = get_elevation_lookup()

    # Build & scale feature vector
    raw_vec = build_feature_vector(body, model_service.feature_names, elevation_lookup)

    try:
        if not model_service.demo_mode and model_service.scaler is not None:
            scaled_vec = model_service.scaler.transform(raw_vec)
        else:
            scaled_vec = raw_vec
    except Exception as e:
        logger.warning(f"Scaler transform failed: {e}. Using raw vector.")
        scaled_vec = raw_vec

    # Predict
    result = model_service.predict(scaled_vec)
    result["probability"] = _override_probability_by_input(body, result["probability"])
    result["prediction"] = int(result["probability"] >= result["threshold"])
    result["confidence_band"] = model_service._confidence_band(result["probability"])

    # SHAP explanations
    raw_explanations = model_service.explain(scaled_vec, top_n=7)
    explanations = humanize_explanation(raw_explanations, model_service.feature_names)

    # Recommendation
    rec = build_recommendation(
        probability=result["probability"],
        district=body.district,
        confidence_band=result["confidence_band"],
    )

    # District info
    district_info = get_district(body.district)
    district_meta = None
    if district_info:
        district_meta = {
            "name": district_info.name,
            "name_ur": district_info.name_ur,
            "province": district_info.province,
            "avg_elevation_m": district_info.avg_elevation_m,
            "terrain_type": district_info.terrain_type,
            "vulnerability_score": district_info.vulnerability_score,
            "rivers": district_info.rivers,
            "flood_history_events": district_info.flood_history_events,
            "ndma_risk_zone": district_info.ndma_risk_zone,
        }

    rec_dict = asdict(rec)

    response = {
        "status": "success",
        "demo_mode": model_service.demo_mode,
        "district": body.district,
        "prediction": {
            "probability": result["probability"],
            "probability_pct": round(result["probability"] * 100, 1),
            "risk_level": rec.risk_level,
            "risk_level_urdu": rec.risk_level_urdu,
            "color": rec.color,
            "alert_level_code": rec.alert_level_code,
        },
        "confidence": {
            "pct": rec.confidence_pct,
            "band": result["confidence_band"],
            "threshold_used": result["threshold"],
        },
        "population_impact": {
            "affected": rec.affected_population,
            "display": rec.affected_population_display,
        },
        "recommendation": rec_dict,
        "explanations": explanations,
        "district_info": district_meta,
        "model_metrics": model_service.metrics,
    }

    return clean_nan(response)