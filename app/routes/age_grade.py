"""Age Grading - WMA tables for running."""
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter()

# WMA 2023 age-grade factors (subset for common distances)
# Format: {distance_m: {age: factor}}
WMA_FACTORS = {
    5000: {30: 1.0000, 35: 0.9685, 40: 0.9370, 45: 0.9055, 50: 0.8740, 55: 0.8425, 60: 0.8110, 65: 0.7795, 70: 0.7480, 75: 0.7165, 80: 0.6850},
    10000: {30: 1.0000, 35: 0.9690, 40: 0.9380, 45: 0.9070, 50: 0.8760, 55: 0.8450, 60: 0.8140, 65: 0.7830, 70: 0.7520, 75: 0.7210, 80: 0.6900},
    21097: {30: 1.0000, 35: 0.9700, 40: 0.9400, 45: 0.9100, 50: 0.8800, 55: 0.8500, 60: 0.8200, 65: 0.7900, 70: 0.7600, 75: 0.7300, 80: 0.7000},
    42195: {30: 1.0000, 35: 0.9710, 40: 0.9420, 45: 0.9130, 50: 0.8840, 55: 0.8550, 60: 0.8260, 65: 0.7970, 70: 0.7680, 75: 0.7390, 80: 0.7100},
}

# Open class standards (seconds) - approximate world records
OPEN_STANDARDS = {
    5000: 12 * 60 + 35,   # 12:35
    10000: 26 * 60 + 11,  # 26:11
    21097: 58 * 60 + 1,   # 58:01
    42195: 2 * 3600 + 0 * 60 + 35,  # 2:00:35
}


class AgeGradeRequest(BaseModel):
    distance_m: int = Field(..., description="Race distance in meters", ge=100)
    time_seconds: float = Field(..., description="Finish time in seconds", gt=0)
    age: int = Field(..., description="Athlete age", ge=10, le=100)
    sex: str = Field("M", description="Sex: M or F", pattern="^[MF]$")


class AgeGradeResponse(BaseModel):
    age_grade_pct: float = Field(..., description="Age-graded performance percentage")
    age_grade_time: float = Field(..., description="Equivalent open-class time (seconds)")
    factor_used: float = Field(..., description="WMA factor applied")
    open_standard: float = Field(..., description="Open class standard (seconds)")


@router.post("/calculate", response_model=AgeGradeResponse, summary="Calculate age-graded performance")
def calculate_age_grade(req: AgeGradeRequest):
    """
    Calculate age-graded performance using WMA 2023 factors.
    
    Age grade % = (open_standard / actual_time) * age_factor * 100
    
    Returns the percentage and the equivalent open-class time.
    """
    # Find closest distance with factors
    distances = sorted(WMA_FACTORS.keys())
    dist = min(distances, key=lambda d: abs(d - req.distance_m))
    
    # Interpolate factor for age
    ages = sorted(WMA_FACTORS[dist].keys())
    if req.age <= ages[0]:
        factor = WMA_FACTORS[dist][ages[0]]
    elif req.age >= ages[-1]:
        factor = WMA_FACTORS[dist][ages[-1]]
    else:
        for i, a in enumerate(ages[:-1]):
            if a <= req.age < ages[i + 1]:
                f1, f2 = WMA_FACTORS[dist][a], WMA_FACTORS[dist][ages[i + 1]]
                factor = f1 + (f2 - f1) * (req.age - a) / (ages[i + 1] - a)
                break
    
    open_std = OPEN_STANDARDS.get(dist, OPEN_STANDARDS[min(OPEN_STANDARDS, key=lambda d: abs(d - req.distance_m))])
    age_grade_time = req.time_seconds / factor
    age_grade_pct = (open_std / age_grade_time) * 100
    
    return AgeGradeResponse(
        age_grade_pct=round(age_grade_pct, 2),
        age_grade_time=round(age_grade_time, 2),
        factor_used=round(factor, 4),
        open_standard=open_std,
    )


@router.get("/factors", summary="Get available WMA factors")
def get_factors(distance_m: int = Query(..., description="Distance in meters")):
    """Return WMA age-grade factors for a distance."""
    distances = sorted(WMA_FACTORS.keys())
    dist = min(distances, key=lambda d: abs(d - distance_m))
    return {"distance_m": dist, "factors": WMA_FACTORS[dist]}