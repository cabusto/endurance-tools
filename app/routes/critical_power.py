"""Critical Power / W' Calculator."""
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
import numpy as np

router = APIRouter()


class CriticalPowerRequest(BaseModel):
    efforts: list[dict] = Field(..., description="List of {duration_sec, power_watts} for 2+ max efforts")


class CriticalPowerResponse(BaseModel):
    cp: float = Field(..., description="Critical Power (watts)")
    w_prime: float = Field(..., description="W' (joules)")
    r_squared: float = Field(..., description="Fit quality")


@router.post("/calculate", response_model=CriticalPowerResponse, summary="Calculate CP and W' from max efforts")
def calculate_cp(req: CriticalPowerRequest):
    """
    Calculate Critical Power (CP) and W' using linear regression:
    
    Work = CP * time + W'
    power * time = CP * time + W'
    power = CP + W' / time
    
    Uses 2+ maximal efforts of different durations (typically 2-20 min).
    """
    if len(req.efforts) < 2:
        raise ValueError("Need at least 2 efforts")
    
    times = np.array([e["duration_sec"] for e in req.efforts])
    powers = np.array([e["power_watts"] for e in req.efforts])
    
    # Linear regression: power = CP + W' * (1/time)
    x = 1 / times
    y = powers
    
    A = np.vstack([x, np.ones_like(x)]).T
    w_prime, cp = np.linalg.lstsq(A, y, rcond=None)[0]
    
    # R-squared
    y_pred = cp + w_prime * x
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    
    return CriticalPowerResponse(
        cp=round(float(cp), 1),
        w_prime=round(float(w_prime), 0),
        r_squared=round(float(r2), 4),
    )


@router.get("/predict", summary="Predict power for a duration given CP/W'")
def predict_power(cp: float = Query(..., gt=0), w_prime: float = Query(..., gt=0), duration_sec: float = Query(..., gt=0)):
    """Predict sustainable power for a given duration."""
    power = cp + w_prime / duration_sec
    return {"duration_sec": duration_sec, "predicted_power": round(power, 1)}