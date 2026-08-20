"""Altitude Adjustment - VO2max/Power derating."""
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter()


class AltitudeRequest(BaseModel):
    altitude_m: float = Field(..., description="Altitude in meters", ge=0)
    metric: str = Field("vo2max", description="Metric to adjust: vo2max, power, pace")
    sea_level_value: float = Field(..., description="Value at sea level", gt=0)


class AltitudeResponse(BaseModel):
    adjusted_value: float
    altitude_m: float
    factor: float
    metric: str


# Altitude derating curves (approximate)
# VO2max drops ~4-5% per 1000m above 1500m
# Power drops ~3-4% per 1000m
# Pace slows ~1-2% per 1000m (running)


@router.post("/adjust", response_model=AltitudeResponse, summary="Adjust performance for altitude")
def adjust(req: AltitudeRequest):
    """
    Apply altitude derating.
    
    Based on published physiology data:
    - VO2max: ~4.5%/1000m above 1500m
    - Power (cycling): ~3.5%/1000m above 1500m  
    - Running pace: ~1.5%/1000m (slower)
    """
    alt = req.altitude_m
    
    if alt <= 1500:
        factor = 1.0
    else:
        km_above = (alt - 1500) / 1000
        if req.metric == "vo2max":
            factor = 1 - 0.045 * km_above
        elif req.metric == "power":
            factor = 1 - 0.035 * km_above
        elif req.metric == "pace":
            factor = 1 + 0.015 * km_above  # pace gets slower (higher)
        else:
            factor = 1.0
    
    factor = max(0.5, min(1.5, factor))  # clamp
    
    if req.metric == "pace":
        adjusted = req.sea_level_value * factor
    else:
        adjusted = req.sea_level_value * factor
    
    return AltitudeResponse(
        adjusted_value=round(adjusted, 2),
        altitude_m=alt,
        factor=round(factor, 4),
        metric=req.metric,
    )


@router.get("/acclimation", summary="Estimate acclimation timeline")
def acclimation(altitude_m: float = Query(..., ge=0)):
    """
    Estimate days to acclimate to altitude.
    
    Rough guideline: 11-14 days per 1000m for full acclimation.
    """
    if altitude_m <= 1500:
        return {"days": 0, "note": "No acclimation needed below 1500m"}
    
    km = altitude_m / 1000
    days = int(12 * km)
    return {
        "altitude_m": altitude_m,
        "estimated_days": days,
        "note": "Individual variation is large; monitor HRV/sleep",
    }