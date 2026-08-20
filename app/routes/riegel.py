"""Riegel Race Time Prediction."""
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter()


class RiegelRequest(BaseModel):
    known_distance_m: int = Field(..., description="Known race distance in meters", ge=100)
    known_time_sec: float = Field(..., description="Known race time in seconds", gt=0)
    target_distance_m: int = Field(..., description="Target distance in meters", ge=100)
    exponent: float = Field(1.06, description="Riegel exponent (default 1.06)")


class RiegelResponse(BaseModel):
    predicted_time_sec: float
    known_distance_m: int
    known_time_sec: float
    target_distance_m: int
    exponent: float


@router.post("/predict", response_model=RiegelResponse, summary="Predict race time using Riegel formula")
def predict(req: RiegelRequest):
    """
    Riegel formula: T2 = T1 * (D2/D1)^exponent
    
    Default exponent 1.06 works well for running. 
    Cycling ~1.05, Swimming ~1.10.
    """
    ratio = req.target_distance_m / req.known_distance_m
    predicted = req.known_time_sec * (ratio ** req.exponent)
    
    return RiegelResponse(
        predicted_time_sec=round(predicted, 1),
        known_distance_m=req.known_distance_m,
        known_time_sec=req.known_time_sec,
        target_distance_m=req.target_distance_m,
        exponent=req.exponent,
    )


@router.get("/common", summary="Predict common race distances from one time")
def common_distances(distance_m: int = Query(...), time_sec: float = Query(...), exponent: float = 1.06):
    """Predict 5k, 10k, half, marathon from any known distance."""
    targets = [5000, 10000, 21097, 42195]
    results = {}
    for d in targets:
        ratio = d / distance_m
        results[f"{d}m"] = round(time_sec * (ratio ** exponent), 1)
    return {"predictions_seconds": results}