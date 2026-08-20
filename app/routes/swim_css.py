"""Swim CSS - Critical Swim Speed from 400/200 time trial."""
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter()


class SwimCSSRequest(BaseModel):
    time_400_sec: float = Field(..., description="400m/yd time trial (seconds)", gt=0)
    time_200_sec: float = Field(..., description="200m/yd time trial (seconds)", gt=0)


class SwimCSSResponse(BaseModel):
    css_sec_per_100: float = Field(..., description="Critical Swim Speed (sec/100m)")
    css_pace_100: str = Field(..., description="CSS as MM:SS per 100m")
    threshold_pace_sec: float = Field(..., description="Anaerobic threshold pace (sec/100m)")
    anaerobic_reserve: float = Field(..., description="Difference between 200 and 400 pace (sec/100m)")


@router.post("/calculate", response_model=SwimCSSResponse, summary="Calculate CSS from 400/200 TT")
def calculate_css(req: SwimCSSRequest):
    """
    Critical Swim Speed (CSS) from two time trials:
    
    CSS (m/s) = (400 - 200) / (time_400 - time_200)
    CSS per 100m = 100 / CSS_mps
    
    Threshold pace ≈ CSS + 1-2 sec/100m
    """
    if req.time_400_sec <= req.time_200_sec:
        raise ValueError("400m time must be slower than 200m time")
    
    # CSS in m/s
    css_mps = 200 / (req.time_400_sec - req.time_200_sec)
    css_per_100 = 100 / css_mps
    
    # Threshold pace (typically CSS + 1.5 sec/100m)
    threshold = css_per_100 + 1.5
    
    # Anaerobic reserve
    pace_200 = req.time_200_sec / 2
    pace_400 = req.time_400_sec / 4
    anaerobic_reserve = pace_200 - pace_400
    
    def fmt(sec):
        m = int(sec // 60)
        s = sec % 60
        return f"{m}:{s:05.2f}"
    
    return SwimCSSResponse(
        css_sec_per_100=round(css_per_100, 2),
        css_pace_100=fmt(css_per_100),
        threshold_pace_sec=round(threshold, 2),
        anaerobic_reserve=round(anaerobic_reserve, 2),
    )


@router.get("/training-zones", summary="Get swim training zones from CSS")
def training_zones(css_sec_per_100: float = Query(..., gt=0)):
    """Return swim training zones based on CSS."""
    zones = [
        ("Recovery", 1.15, 1.25),
        ("Aerobic", 1.05, 1.15),
        ("Threshold", 0.98, 1.05),
        ("VO2max", 0.92, 0.98),
        ("Speed", 0.85, 0.92),
    ]
    
    result = []
    for name, low, high in zones:
        result.append({
            "zone": name,
            "min_sec_per_100": round(css_sec_per_100 * low, 2),
            "max_sec_per_100": round(css_sec_per_100 * high, 2),
        })
    
    return {"css_sec_per_100": css_sec_per_100, "zones": result}