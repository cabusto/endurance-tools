"""Endurance API - Unified calculations for endurance sports."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import age_grade, vdot, cat_ranking, fina_points, critical_power, riegel, purdy, tss, hr_zones, pace_convert, altitude, heat, swim_css, bike_fit

app = FastAPI(
    title="Endurance API",
    version="0.1.0",
    description="Calculations for running, cycling, swimming, and triathlon.",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(age_grade.router, prefix="/age-grade", tags=["Age Grading"])
app.include_router(vdot.router, prefix="/vdot", tags=["VDOT"])
app.include_router(cat_ranking.router, prefix="/cat-ranking", tags=["Cycling Category"])
app.include_router(fina_points.router, prefix="/fina", tags=["FINA Points"])
app.include_router(critical_power.router, prefix="/critical-power", tags=["Critical Power"])
app.include_router(riegel.router, prefix="/riegel", tags=["Race Prediction"])
app.include_router(purdy.router, prefix="/purdy", tags=["Purdy Points"])
app.include_router(tss.router, prefix="/tss", tags=["Training Stress"])
app.include_router(hr_zones.router, prefix="/hr-zones", tags=["Heart Rate Zones"])
app.include_router(pace_convert.router, prefix="/pace", tags=["Pace Conversion"])
app.include_router(altitude.router, prefix="/altitude", tags=["Altitude Adjustment"])
app.include_router(heat.router, prefix="/heat", tags=["Heat Adjustment"])
app.include_router(swim_css.router, prefix="/swim-css", tags=["Swim CSS"])
app.include_router(bike_fit.router, prefix="/bike-fit", tags=["Bike Fit"])


@app.get("/", include_in_schema=False)
def root():
    return {"name": "Endurance API", "version": "0.1.0", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}