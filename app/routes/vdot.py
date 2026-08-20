"""VDOT - Jack Daniels running calculator."""
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
import math

router = APIRouter()

# VDOT lookup table (VDOT -> VO2max ml/kg/min approx)
# Daniels' approximate mapping
VDOT_TO_VO2 = {v: v for v in range(30, 85)}  # VDOT ~= VO2max for our purposes


class VDOTRequest(BaseModel):
    distance_m: int = Field(..., description="Race distance in meters", ge=100)
    time_seconds: float = Field(..., description="Finish time in seconds", gt=0)


class VDOTResponse(BaseModel):
    vdot: float = Field(..., description="Calculated VDOT score")
    vo2max_est: float = Field(..., description="Estimated VO2max (ml/kg/min)")
    training_paces: dict = Field(..., description="Training paces (sec/km)")


# Standard training paces as % of VDOT pace
PACE_PERCENTAGES = {
    "E": 0.65,   # Easy
    "M": 0.82,   # Marathon
    "T": 0.88,   # Threshold
    "I": 0.98,   # Interval
    "R": 1.05,   # Repetition
}


@router.post("/calculate", response_model=VDOTResponse, summary="Calculate VDOT from race performance")
def calculate_vdot(req: VDOTRequest):
    """
    Calculate VDOT from a race time using Jack Daniels' formula.
    
    VDOT = (VO2max * 100) / (percent_max * oxygen_cost)
    Simplified: VDOT ≈ (velocity_mps * 60 * 1000) / (3.5 + distance_factor)
    """
    # Oxygen cost of running (ml/kg/km) - simplified Daniels
    # VO2 = 3.5 + 0.2 * velocity_mpm
    velocity_mps = req.distance_m / req.time_seconds
    velocity_mpm = velocity_mps * 60
    
    # Daniels' VDOT calculation
    # VO2 = -4.60 + 0.182258 * velocity + 0.000104 * velocity^2
    vo2 = -4.60 + 0.182258 * velocity_mpm + 0.000104 * velocity_mpm ** 2
    
    # Percent of max VO2 for this distance (Daniels' curves)
    if req.distance_m <= 1500:
        pct_max = 1.0
    elif req.distance_m <= 3000:
        pct_max = 0.95
    elif req.distance_m <= 5000:
        pct_max = 0.90
    elif req.distance_m <= 10000:
        pct_max = 0.88
    elif req.distance_m <= 21097:
        pct_max = 0.85
    else:
        pct_max = 0.82
    
    vdot = vo2 / pct_max
    vdot = round(vdot, 1)
    
    # Training paces in sec/km
    vdot_velocity = vdot * pct_max  # m/min at VDOT
    training_paces = {}
    for label, pct in PACE_PERCENTAGES.items():
        pace_mpm = vdot_velocity * pct  # m/min at this intensity
        pace_sec_km = 1000 / (pace_mpm / 60) if pace_mpm > 0 else 0
        training_paces[label] = round(pace_sec_km, 1)
    
    return VDOTResponse(
        vdot=vdot,
        vo2max_est=round(vo2, 1),
        training_paces=training_paces,
    )


@router.get("/paces", summary="Get training paces for a VDOT")
def get_paces(vdot: float = Query(..., ge=30, le=85)):
    """Return training paces (sec/km) for a given VDOT."""
    vdot_velocity = vdot * 0.85  # approximate
    paces = {}
    for label, pct in PACE_PERCENTAGES.items():
        pace_mpm = vdot_velocity * pct
        pace_sec_km = 1000 / (pace_mpm / 60) if pace_mpm > 0 else 0
        paces[label] = round(pace_sec_km, 1)
    return {"vdot": vdot, "training_paces_sec_per_km": paces}


@router.get("/race-times", summary="Predict race times for a VDOT")
def predict_times(vdot: float = Query(..., ge=30, le=85)):
    """Predict race times for common distances at a given VDOT."""
    distances = [1500, 3000, 5000, 10000, 21097, 42195]
    results = {}
    for d in distances:
        if d <= 1500:
            pct = 1.0
        elif d <= 3000:
            pct = 0.95
        elif d <= 5000:
            pct = 0.90
        elif d <= 10000:
            pct = 0.88
        elif d <= 21097:
            pct = 0.85
        else:
            pct = 0.82
        
        vo2 = vdot * pct
        # Reverse solve for velocity: VO2 = -4.60 + 0.182258*v + 0.000104*v^2
        # 0.000104*v^2 + 0.182258*v - (4.60 + VO2) = 0
        a, b, c = 0.000104, 0.182258, -(4.60 + vo2)
        disc = b**2 - 4*a*c
        if disc > 0:
            v_mpm = (-b + disc**0.5) / (2*a)
            time_sec = d / (v_mpm / 60)
            results[f"{d}m"] = round(time_sec, 1)
    return {"vdot": vdot, "predicted_times_seconds": results}