"""Bike Fit - Anthropometric calculations."""
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter()


class BikeFitRequest(BaseModel):
    height_cm: float = Field(..., description="Rider height in cm", gt=0)
    inseam_cm: float = Field(..., description="Inseam in cm", gt=0)
    gender: str = Field("M", description="Gender: M or F", pattern="^[MF]$")
    style: str = Field("road", description="Bike style: road, tt, mtb, gravel")


class BikeFitResponse(BaseModel):
    saddle_height_mm: float
    saddle_setback_mm: float
    reach_mm: float
    stack_mm: float
    handlebar_drop_mm: float
    crank_length_mm: float
    notes: list[str]


@router.post("/calculate", response_model=BikeFitResponse, summary="Calculate bike fit from anthropometrics")
def calculate_fit(req: BikeFitRequest):
    """
    Calculate bike fit measurements from body dimensions.
    
    Based on common fit systems (Lemond, Greg LeMond, BikeFit, etc.)
    These are starting points - professional fit recommended.
    """
    h = req.height_cm
    i = req.inseam_cm
    
    # Saddle height (BB to saddle top along seat tube)
    # Lemond: 0.883 * inseam
    saddle_height = i * 0.883
    
    # Saddle setback (behind BB) - KOPS approximation
    # Femur length ≈ 0.27 * height
    femur = h * 0.27
    setback = femur * 0.3  # rough KOPS
    
    # Reach and stack (frame sizing)
    # Road: reach ≈ 0.4 * height, stack ≈ 0.52 * height
    if req.style == "road":
        reach = h * 0.40
        stack = h * 0.52
        drop = h * 0.06
    elif req.style == "tt":
        reach = h * 0.42
        stack = h * 0.48
        drop = h * 0.10
    elif req.style == "mtb":
        reach = h * 0.38
        stack = h * 0.56
        drop = h * 0.02
    else:  # gravel
        reach = h * 0.39
        stack = h * 0.54
        drop = h * 0.04
    
    # Crank length
    # Common formula: 0.216 * inseam (mm) or height-based
    crank = i * 2.16  # mm
    crank = round(crank / 2.5) * 2.5  # round to 2.5mm
    crank = max(160, min(180, crank))  # clamp to common range
    
    notes = [
        "Starting points only - professional fit recommended",
        f"Saddle height: {saddle_height:.0f}mm (BB to saddle top)",
        f"Crank length: {crank:.0f}mm (common range 165-175mm)",
        "Adjust for flexibility, riding style, injury history",
    ]
    
    if req.gender == "F":
        notes.append("Women may prefer slightly shorter reach, higher stack")
    
    return BikeFitResponse(
        saddle_height_mm=round(saddle_height, 1),
        saddle_setback_mm=round(setback, 1),
        reach_mm=round(reach, 1),
        stack_mm=round(stack, 1),
        handlebar_drop_mm=round(drop, 1),
        crank_length_mm=round(crank, 1),
        notes=notes,
    )


@router.get("/crank-length", summary="Crank length recommendations by inseam")
def crank_length(inseam_cm: float = Query(..., gt=0)):
    """Crank length suggestions based on inseam."""
    # Various formulas
    lemond = inseam_cm * 2.16
    bikefit = inseam_cm * 2.14
    graham = inseam_cm * 2.19
    
    return {
        "inseam_cm": inseam_cm,
        "formulas_mm": {
            "lemond": round(lemond, 1),
            "bikefit": round(bikefit, 1),
            "graham_obree": round(graham, 1),
        },
        "common_sizes_mm": [160, 162.5, 165, 167.5, 170, 172.5, 175, 177.5, 180],
    }