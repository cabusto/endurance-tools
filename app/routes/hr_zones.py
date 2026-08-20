"""Heart Rate Zones - Multiple zone systems."""
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter()


class HRZonesRequest(BaseModel):
    max_hr: float = Field(..., description="Max heart rate (bpm)", gt=0)
    resting_hr: float | None = Field(None, description="Resting HR (bpm) - needed for Karvonen")
    system: str = Field("coggan", description="Zone system: coggan, british, karvonen, garmin")


class HRZone(BaseModel):
    zone: int
    name: str
    min_bpm: float
    max_bpm: float
    pct_max: tuple[float, float] | None = None
    pct_hrr: tuple[float, float] | None = None


class HRZonesResponse(BaseModel):
    zones: list[HRZone]
    system: str
    max_hr: float
    resting_hr: float | None


# Coggan zones (% of max HR)
COGGAN = [
    (1, "Active Recovery", 0, 0.55),
    (2, "Endurance", 0.55, 0.75),
    (3, "Tempo", 0.75, 0.90),
    (4, "Threshold", 0.90, 1.00),
    (5, "VO2max", 1.00, 1.05),
    (6, "Anaerobic", 1.05, 1.20),
    (7, "Neuromuscular", 1.20, 1.50),
]

# British Cycling zones
BRITISH = [
    (1, "Recovery", 0, 0.60),
    (2, "Endurance", 0.60, 0.70),
    (3, "Tempo", 0.70, 0.80),
    (4, "Threshold", 0.80, 0.90),
    (5, "VO2max", 0.90, 1.00),
    (6, "Anaerobic", 1.00, 1.10),
]

# Garmin zones
GARMIN = [
    (1, "Warm Up", 0.50, 0.60),
    (2, "Easy", 0.60, 0.70),
    (3, "Aerobic", 0.70, 0.80),
    (4, "Threshold", 0.80, 0.90),
    (5, "Maximum", 0.90, 1.00),
]


@router.post("/calculate", response_model=HRZonesResponse, summary="Calculate HR zones")
def calculate_zones(req: HRZonesRequest):
    """
    Calculate heart rate zones for various systems.
    
    Systems:
    - coggan: Andy Coggan 7-zone (default)
    - british: British Cycling 6-zone
    - garmin: Garmin 5-zone
    - karvonen: Karvonen (%HRR) - requires resting_hr
    """
    if req.system == "karvonen" and req.resting_hr is None:
        raise ValueError("resting_hr required for Karvonen system")
    
    if req.system == "coggan":
        zone_defs = COGGAN
    elif req.system == "british":
        zone_defs = BRITISH
    elif req.system == "garmin":
        zone_defs = GARMIN
    elif req.system == "karvonen":
        return _karvonen_zones(req.max_hr, req.resting_hr)
    else:
        zone_defs = COGGAN
    
    zones = []
    for z, name, pct_min, pct_max in zone_defs:
        zones.append(HRZone(
            zone=z,
            name=name,
            min_bpm=round(req.max_hr * pct_min),
            max_bpm=round(req.max_hr * pct_max),
            pct_max=(round(pct_min * 100, 1), round(pct_max * 100, 1)),
        ))
    
    return HRZonesResponse(
        zones=zones,
        system=req.system,
        max_hr=req.max_hr,
        resting_hr=req.resting_hr,
    )


def _karvonen_zones(max_hr: float, resting_hr: float) -> HRZonesResponse:
    """Karvonen zones based on heart rate reserve."""
    hrr = max_hr - resting_hr
    # Standard Karvonen zones
    karvonen_defs = [
        (1, "Recovery", 0.50, 0.60),
        (2, "Endurance", 0.60, 0.70),
        (3, "Tempo", 0.70, 0.80),
        (4, "Threshold", 0.80, 0.90),
        (5, "VO2max", 0.90, 1.00),
    ]
    
    zones = []
    for z, name, pct_min, pct_max in karvonen_defs:
        min_bpm = resting_hr + hrr * pct_min
        max_bpm = resting_hr + hrr * pct_max
        zones.append(HRZone(
            zone=z,
            name=name,
            min_bpm=round(min_bpm),
            max_bpm=round(max_bpm),
            pct_hrr=(round(pct_min * 100, 1), round(pct_max * 100, 1)),
        ))
    
    return HRZonesResponse(
        zones=zones,
        system="karvonen",
        max_hr=max_hr,
        resting_hr=resting_hr,
    )


@router.get("/systems", summary="List available zone systems")
def list_systems():
    return {"systems": ["coggan", "british", "garmin", "karvonen"]}