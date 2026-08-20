"""Cycling Category Ranking - USAC/Zwift FTP-based categories."""
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter()

# USAC category thresholds (FTP w/kg)
# Men
USAC_MEN = {
    "Pro": 6.0,
    "Cat 1": 5.5,
    "Cat 2": 5.0,
    "Cat 3": 4.5,
    "Cat 4": 4.0,
    "Cat 5": 0.0,
}

# Women
USAC_WOMEN = {
    "Pro": 5.3,
    "Cat 1": 4.8,
    "Cat 2": 4.3,
    "Cat 3": 3.8,
    "Cat 4": 3.3,
    "Cat 5": 0.0,
}

# Zwift racing categories (FTP w/kg)
ZWIFT = {
    "A": 4.0,
    "B": 3.2,
    "C": 2.5,
    "D": 0.0,
}

# Zwift CE (Category Enforcement) - more granular
ZWIFT_CE = {
    "A+": 4.8,
    "A": 4.0,
    "B": 3.2,
    "C": 2.5,
    "D": 1.8,
    "E": 0.0,
}


class CatRankingRequest(BaseModel):
    ftp_watts: float = Field(..., description="FTP in watts", gt=0)
    weight_kg: float = Field(..., description="Body weight in kg", gt=0)
    sex: str = Field("M", description="Sex: M or F", pattern="^[MF]$")
    system: str = Field("usac", description="Ranking system: usac, zwift, zwift-ce")


class CatRankingResponse(BaseModel):
    category: str = Field(..., description="Assigned category")
    ftp_wkg: float = Field(..., description="FTP in watts/kg")
    thresholds: dict = Field(..., description="All thresholds for reference")
    next_category: str | None = Field(None, description="Next category up")
    watts_to_next: float | None = Field(None, description="Watts needed for next category")


@router.post("/calculate", response_model=CatRankingResponse, summary="Calculate cycling category from FTP")
def calculate_category(req: CatRankingRequest):
    """
    Determine cycling category from FTP w/kg.
    
    Systems:
    - usac: USA Cycling categories (sex-specific)
    - zwift: Zwift racing categories (A-D)
    - zwift-ce: Zwift Category Enforcement (A+ through E)
    """
    ftp_wkg = req.ftp_watts / req.weight_kg
    
    if req.system == "usac":
        thresholds = USAC_WOMEN if req.sex == "F" else USAC_MEN
    elif req.system == "zwift":
        thresholds = ZWIFT
    elif req.system == "zwift-ce":
        thresholds = ZWIFT_CE
    else:
        thresholds = USAC_MEN if req.sex == "M" else USAC_WOMEN
    
    # Find category (highest threshold met)
    sorted_cats = sorted(thresholds.items(), key=lambda x: x[1], reverse=True)
    category = sorted_cats[-1][0]
    next_cat = None
    watts_to_next = None
    
    for i, (cat, thresh) in enumerate(sorted_cats):
        if ftp_wkg >= thresh:
            category = cat
            if i > 0:
                next_cat = sorted_cats[i - 1][0]
                watts_to_next = round((sorted_cats[i - 1][1] - ftp_wkg) * req.weight_kg, 1)
            break
    
    return CatRankingResponse(
        category=category,
        ftp_wkg=round(ftp_wkg, 2),
        thresholds=thresholds,
        next_category=next_cat,
        watts_to_next=watts_to_next,
    )


@router.get("/thresholds", summary="Get category thresholds for a system")
def get_thresholds(system: str = Query("usac", pattern="^(usac|zwift|zwift-ce)$"), sex: str = Query("M", pattern="^[MF]$")):
    """Return all category thresholds for a system."""
    if system == "usac":
        return {"system": "usac", "sex": sex, "thresholds": USAC_WOMEN if sex == "F" else USAC_MEN}
    elif system == "zwift":
        return {"system": "zwift", "thresholds": ZWIFT}
    else:
        return {"system": "zwift-ce", "thresholds": ZWIFT_CE}