"""FINA Points - Swimming scoring (cubic formula)."""
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter()

# FINA base times (seconds) for 1000 points - 2024 standards (subset)
# Format: {event: {sex: base_time}}
FINA_BASE = {
    "50_free": {"M": 20.91, "F": 23.67},
    "100_free": {"M": 46.91, "F": 51.71},
    "200_free": {"M": 102.00, "F": 113.00},
    "400_free": {"M": 218.00, "F": 238.00},
    "800_free": {"M": 460.00, "F": 505.00},
    "1500_free": {"M": 880.00, "F": 960.00},
    "50_back": {"M": 23.55, "F": 26.98},
    "100_back": {"M": 51.85, "F": 57.57},
    "200_back": {"M": 113.00, "F": 126.00},
    "50_breast": {"M": 25.95, "F": 29.30},
    "100_breast": {"M": 56.88, "F": 104.00},
    "200_breast": {"M": 124.00, "F": 138.00},
    "50_fly": {"M": 22.27, "F": 25.07},
    "100_fly": {"M": 49.82, "F": 55.48},
    "200_fly": {"M": 109.00, "F": 121.00},
    "200_im": {"M": 113.00, "F": 125.00},
    "400_im": {"M": 235.00, "F": 255.00},
}


class FinaRequest(BaseModel):
    event: str = Field(..., description="Event key (e.g., 100_free, 200_fly)")
    time_seconds: float = Field(..., description="Swim time in seconds", gt=0)
    sex: str = Field("M", description="Sex: M or F", pattern="^[MF]$")


class FinaResponse(BaseModel):
    points: int = Field(..., description="FINA points")
    event: str
    sex: str
    base_time: float
    time_seconds: float


@router.post("/calculate", response_model=FinaResponse, summary="Calculate FINA points from swim time")
def calculate_fina(req: FinaRequest):
    """
    Calculate FINA points using the cubic formula:
    
    Points = 1000 * (base_time / time)^3
    
    Base times are the 2024 FINA 1000-point standards.
    """
    if req.event not in FINA_BASE:
        raise ValueError(f"Unknown event: {req.event}. Available: {list(FINA_BASE.keys())}")
    
    base = FINA_BASE[req.event][req.sex]
    points = 1000 * (base / req.time_seconds) ** 3
    points = int(points)
    
    return FinaResponse(
        points=points,
        event=req.event,
        sex=req.sex,
        base_time=base,
        time_seconds=req.time_seconds,
    )


@router.get("/base-times", summary="Get FINA base times (1000-point standards)")
def get_base_times(sex: str = Query("M", pattern="^[MF]$")):
    """Return all base times for a sex."""
    return {"sex": sex, "base_times": {e: v[sex] for e, v in FINA_BASE.items()}}


@router.get("/events", summary="List supported events")
def list_events():
    """List all supported swimming events."""
    return {"events": sorted(FINA_BASE.keys())}