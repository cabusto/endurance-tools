"""Heat/WBGT Adjustment - Pace/Power derating for temperature."""
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter()


class HeatRequest(BaseModel):
    temperature_c: float = Field(..., description="Air temperature in Celsius")
    humidity_pct: float = Field(50, description="Relative humidity %", ge=0, le=100)
    metric: str = Field("pace", description="Metric to adjust: pace, power")
    base_value: float = Field(..., description="Base value (sec/km for pace, watts for power)", gt=0)


class HeatResponse(BaseModel):
    adjusted_value: float
    wbgt_c: float
    factor: float
    risk_level: str


@router.post("/adjust", response_model=HeatResponse, summary="Adjust performance for heat")
def adjust(req: HeatRequest):
    """
    Adjust pace/power for heat using WBGT approximation.
    
    WBGT ≈ 0.7 * Twb + 0.2 * Tglobe + 0.1 * Tair
    Simplified: WBGT ≈ Tair * (0.5 + 0.5 * humidity/100) for still air
    
    Derating (ACSMM/IOC guidelines):
    - WBGT < 10°C: minimal impact
    - WBGT 10-18°C: ~1-3% pace slowdown
    - WBGT 18-28°C: ~3-7% slowdown
    - WBGT > 28°C: high risk, >10% slowdown
    """
    # Simplified WBGT
    wbgt = req.temperature_c * (0.5 + 0.5 * req.humidity_pct / 100)
    
    if wbgt < 10:
        factor = 1.0
        risk = "Low"
    elif wbgt < 18:
        factor = 1.0 + 0.02 * (wbgt - 10)  # 1-3%
        risk = "Moderate"
    elif wbgt < 28:
        factor = 1.03 + 0.04 * (wbgt - 18)  # 3-7%
        risk = "High"
    else:
        factor = 1.43 + 0.05 * (wbgt - 28)  # >10%
        risk = "Extreme"
    
    factor = min(factor, 1.5)  # cap
    
    if req.metric == "pace":
        adjusted = req.base_value * factor
    else:
        adjusted = req.base_value / factor  # power drops
    
    return HeatResponse(
        adjusted_value=round(adjusted, 2),
        wbgt_c=round(wbgt, 1),
        factor=round(factor, 3),
        risk_level=risk,
    )


@router.get("/guidelines", summary="Heat risk guidelines")
def guidelines():
    return {
        "wbgt_ranges": [
            {"range": "< 10°C", "risk": "Low", "action": "Normal training"},
            {"range": "10-18°C", "risk": "Moderate", "action": "Increase hydration, monitor effort"},
            {"range": "18-28°C", "risk": "High", "action": "Reduce intensity, extra cooling"},
            {"range": "> 28°C", "risk": "Extreme", "action": "Cancel or move indoors"},
        ]
    }