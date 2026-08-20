"""Pace/Speed Unit Conversion."""
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter()


class PaceConvertRequest(BaseModel):
    value: float = Field(..., description="Input value", gt=0)
    from_unit: str = Field(..., description="Source unit: min_per_km, min_per_mi, kmh, mph, sec_per_100m, sec_per_100y")
    to_unit: str = Field(..., description="Target unit")


class PaceConvertResponse(BaseModel):
    result: float
    from_unit: str
    to_unit: str
    input_value: float


UNITS = {
    "min_per_km": ("pace", 1000 / 60),      # m/s per min/km
    "min_per_mi": ("pace", 1609.344 / 60),   # m/s per min/mi
    "kmh": ("speed", 1000 / 3600),           # m/s per km/h
    "mph": ("speed", 1609.344 / 3600),       # m/s per mph
    "sec_per_100m": ("pace", 100),           # m/s per sec/100m
    "sec_per_100y": ("pace", 91.44),         # m/s per sec/100y
}


def to_mps(value: float, unit: str) -> float:
    """Convert any pace/speed unit to m/s."""
    utype, factor = UNITS[unit]
    if utype == "pace":
        return factor / value
    else:
        return value * factor


def from_mps(mps: float, unit: str) -> float:
    """Convert m/s to any pace/speed unit."""
    utype, factor = UNITS[unit]
    if utype == "pace":
        return factor / mps
    else:
        return mps / factor


@router.post("/convert", response_model=PaceConvertResponse, summary="Convert between pace/speed units")
def convert(req: PaceConvertRequest):
    """
    Convert between pace and speed units.
    
    Supported units:
    - min_per_km: minutes per kilometer (running)
    - min_per_mi: minutes per mile (running)
    - kmh: kilometers per hour (cycling)
    - mph: miles per hour (cycling)
    - sec_per_100m: seconds per 100m (swimming)
    - sec_per_100y: seconds per 100 yards (swimming SCY)
    """
    if req.from_unit not in UNITS or req.to_unit not in UNITS:
        raise ValueError(f"Unknown unit. Supported: {list(UNITS.keys())}")
    
    mps = to_mps(req.value, req.from_unit)
    result = from_mps(mps, req.to_unit)
    
    return PaceConvertResponse(
        result=round(result, 2),
        from_unit=req.from_unit,
        to_unit=req.to_unit,
        input_value=req.value,
    )


@router.get("/swim-convert", summary="Convert swim paces between pool types")
def swim_convert(pace_sec_per_100: float = Query(..., gt=0), from_pool: str = Query(..., pattern="^(scm|lcm|scy)$"), to_pool: str = Query(..., pattern="^(scm|lcm|scy)$")):
    """
    Convert swim pace between pool types.
    
    SCM = short course meters (25m)
    LCM = long course meters (50m)
    SCY = short course yards (25y)
    
    Uses standard conversion factors.
    """
    # Conversion factors relative to SCM
    factors = {
        "scm": 1.0,
        "lcm": 1.03,   # LCM ~3% slower
        "scy": 0.90,   # SCY ~10% faster (shorter distance)
    }
    
    scm_pace = pace_sec_per_100 / factors[from_pool]
    result = scm_pace * factors[to_pool]
    
    return {
        "input": {"pace_sec_per_100": pace_sec_per_100, "from_pool": from_pool},
        "output": {"pace_sec_per_100": round(result, 2), "to_pool": to_pool},
    }