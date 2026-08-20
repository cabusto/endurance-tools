"""Purdy Points - Running scoring system."""
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter()

# Purdy points table: time (seconds) -> points for standard distances
# This is a simplified subset; full tables are much larger
PURDY_TABLE = {
    1500: {210: 1000, 240: 900, 270: 800, 300: 700, 330: 600, 360: 500, 390: 400, 420: 300, 450: 200, 480: 100},
    5000: {780: 1000, 900: 900, 1020: 800, 1140: 700, 1260: 600, 1380: 500, 1500: 400, 1620: 300, 1740: 200, 1860: 100},
    10000: {1680: 1000, 1860: 900, 2040: 800, 2220: 700, 2400: 600, 2580: 500, 2760: 400, 2940: 300, 3120: 200, 3300: 100},
    42195: {7500: 1000, 8400: 900, 9300: 800, 10200: 700, 11100: 600, 12000: 500, 12900: 400, 13800: 300, 14700: 200, 15600: 100},
}


class PurdyRequest(BaseModel):
    distance_m: int = Field(..., description="Race distance in meters", ge=100)
    time_seconds: float = Field(..., description="Finish time in seconds", gt=0)


class PurdyResponse(BaseModel):
    points: int = Field(..., description="Purdy points")
    distance_m: int
    time_seconds: float


@router.post("/calculate", response_model=PurdyResponse, summary="Calculate Purdy points")
def calculate_purdy(req: PurdyRequest):
    """
    Calculate Purdy points by linear interpolation in the table.
    
    Purdy points are an older running scoring system, similar to age grading
    but without age/sex adjustment.
    """
    distances = sorted(PURDY_TABLE.keys())
    dist = min(distances, key=lambda d: abs(d - req.distance_m))
    
    table = PURDY_TABLE[dist]
    times = sorted(table.keys())
    points = [table[t] for t in times]
    
    # Interpolate
    if req.time_seconds <= times[0]:
        purdy_points = points[0]
    elif req.time_seconds >= times[-1]:
        purdy_points = points[-1]
    else:
        for i, t in enumerate(times[:-1]):
            if t <= req.time_seconds < times[i + 1]:
                p1, p2 = points[i], points[i + 1]
                purdy_points = p1 + (p2 - p1) * (req.time_seconds - t) / (times[i + 1] - t)
                break
    
    return PurdyResponse(
        points=int(round(purdy_points)),
        distance_m=dist,
        time_seconds=req.time_seconds,
    )