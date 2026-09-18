"""Endurance API - Unified calculations for endurance sports."""
from copy import deepcopy

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from .routes import age_grade, vdot, cat_ranking, fina_points, critical_power, riegel, purdy, tss, hr_zones, pace_convert, altitude, heat, swim_css, bike_fit

GUIDANCE = """Use this API as a calculation toolbox for endurance sports.

Discovery and invocation guidance:
- Treat `/openapi.json` as the canonical discovery contract.
- Prefer JSON request bodies when an operation exposes one.
- For query-style helper endpoints, use the documented query parameters; the OpenAPI spec mirrors those inputs in a JSON schema for discovery.
- Routes are public and intentionally open unless a security scheme is explicitly attached.
- The API is organized by sport and calculation type: running, cycling, swimming, triathlon, and general pacing/conditioning utilities.
- Endpoints return deterministic math or table lookups, so they are safe to call repeatedly with the same inputs.
"""

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


def _synthesize_request_body(operation: dict) -> None:
    if operation.get("requestBody") or not operation.get("parameters"):
        return

    props = {}
    required = []
    for param in operation["parameters"]:
        if param.get("in") != "query":
            continue
        schema = deepcopy(param.get("schema", {}))
        if not schema:
            continue
        props[param["name"]] = schema
        if param.get("required"):
            required.append(param["name"])

    if props:
        operation["requestBody"] = {
            "required": bool(required),
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": props,
                        "required": required,
                        "additionalProperties": False,
                    }
                }
            },
        }


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    schema.setdefault("info", {})
    schema["info"]["contact"] = {"email": "justinkwarren@gmail.com"}
    schema["info"]["x-guidance"] = GUIDANCE

    schema.setdefault("components", {})
    schema["components"].setdefault("securitySchemes", {})
    schema["components"]["securitySchemes"]["siwx"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "SIWX",
        "description": "Identity-only SIWX bearer token.",
    }

    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            operation["security"] = []
            _synthesize_request_body(operation)

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/", include_in_schema=False)
def root():
    return {"name": "Endurance API", "version": "0.1.0", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}