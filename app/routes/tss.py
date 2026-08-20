"""Training Stress Score (TSS) and TRIMP."""
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter()


class TSSRequest(BaseModel):
    ftp_watts: float = Field(..., description="Functional Threshold Power (watts)", gt=0)
    np_watts: float = Field(..., description="Normalized Power for the ride (watts)", gt=0)
    duration_sec: float = Field(..., description="Ride duration in seconds", gt=0)


class TSSResponse(BaseModel):
    tss: float
    if_factor: float
    duration_hours: float


@router.post("/tss", response_model=TSSResponse, summary="Calculate TSS from power data")
def calculate_tss(req: TSSRequest):
    """
    TSS = (duration_hr * NP * IF) / (FTP * 3600) * 100
    where IF = NP / FTP
    
    Simplifies to: TSS = duration_hr * IF^2 * 100
    """
    if_factor = req.np_watts / req.ftp_watts
    duration_hr = req.duration_sec / 3600
    tss = duration_hr * if_factor ** 2 * 100
    
    return TSSResponse(
        tss=round(tss, 1),
        if_factor=round(if_factor, 3),
        duration_hours=round(duration_hr, 2),
    )


class TrimpRequest(BaseModel):
    avg_hr: float = Field(..., description="Average heart rate (bpm)", gt=0)
    max_hr: float = Field(..., description="Max heart rate (bpm)", gt=0)
    resting_hr: float = Field(..., description="Resting heart rate (bpm)", gt=0)
    duration_min: float = Field(..., description="Duration in minutes", gt=0)
    sex: str = Field("M", description="Sex: M or F", pattern="^[MF]$")


class TrimpResponse(BaseModel):
    trimp: float
    hr_reserve_pct: float


@router.post("/trimp", response_model=TrimpResponse, summary="Calculate TRIMP from HR data")
def calculate_trimp(req: TrimpRequest):
    """
    TRIMP (Training Impulse) - Banister's method:
    
    TRIMP = duration_min * HRR_fraction * exp(1.92 * HRR_fraction) for men
    TRIMP = duration_min * HRR_fraction * exp(1.67 * HRR_fraction) for women
    
    where HRR_fraction = (avg_hr - resting_hr) / (max_hr - resting_hr)
    """
    hr_reserve = req.max_hr - req.resting_hr
    if hr_reserve <= 0:
        raise ValueError("max_hr must be > resting_hr")
    
    hrr_fraction = (req.avg_hr - req.resting_hr) / hr_reserve
    hrr_fraction = max(0, min(1, hrr_fraction))  # clamp
    
    coeff = 1.92 if req.sex == "M" else 1.67
    trimp = req.duration_min * hrr_fraction * (2.71828 ** (coeff * hrr_fraction))
    
    return TrimpResponse(
        trimp=round(trimp, 1),
        hr_reserve_pct=round(hrr_fraction * 100, 1),
    )