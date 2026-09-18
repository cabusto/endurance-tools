"""Endurance API - Unified calculations for endurance sports."""
from copy import deepcopy
import asyncio
import hashlib
import json
import os
from urllib.parse import urlparse
from urllib.request import Request as UrlRequest, urlopen
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from starlette.background import BackgroundTask
from starlette.responses import JSONResponse

from .routes import age_grade, vdot, cat_ranking, fina_points, critical_power, riegel, purdy, tss, hr_zones, pace_convert, altitude, heat, swim_css, bike_fit
from .static_favicon import router as favicon_router

PUBLIC_ORIGIN = os.getenv("PUBLIC_ORIGIN", "https://endurance-tools-kappa.vercel.app")
PUBLIC_ORIGIN_HOST = urlparse(PUBLIC_ORIGIN).netloc or PUBLIC_ORIGIN.replace("https://", "").replace("http://", "")
GUIDANCE = """Use this API as a calculation toolbox for endurance sports.

Discovery and invocation guidance:
- Treat `/openapi.json` as the canonical discovery contract.
- Free reference routes are intentionally open and declared with `security: []`.
- Paid calculators challenge with HTTP 402 and `WWW-Authenticate` before body/query validation runs.
- Prefer JSON request bodies when an operation exposes one.
- For query-style helper endpoints, use the documented query parameters; the OpenAPI spec mirrors those inputs in a JSON schema for discovery.
- The API is organized by sport and calculation type: running, cycling, swimming, triathlon, and general pacing/conditioning utilities.
- Endpoints return deterministic math or table lookups, so they are safe to call repeatedly with the same inputs.
"""

PAID_ENDPOINTS = {
    ("POST", "/age-grade/calculate"): 0.05,
    ("POST", "/vdot/calculate"): 0.05,
    ("POST", "/cat-ranking/calculate"): 0.05,
    ("POST", "/fina/calculate"): 0.05,
    ("POST", "/critical-power/calculate"): 0.05,
    ("POST", "/riegel/predict"): 0.05,
    ("POST", "/purdy/calculate"): 0.05,
    ("POST", "/tss/tss"): 0.05,
    ("POST", "/tss/trimp"): 0.05,
    ("POST", "/hr-zones/calculate"): 0.05,
    ("POST", "/pace/convert"): 0.05,
    ("POST", "/altitude/adjust"): 0.05,
    ("POST", "/heat/adjust"): 0.05,
    ("POST", "/swim-css/calculate"): 0.05,
    ("POST", "/bike-fit/calculate"): 0.05,
}

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

PAYMENT_ENFORCEMENT = os.getenv("ENFORCE_PAYMENTS", os.getenv("VERCEL") == "1")
POSTHOG_ENABLED = bool(os.getenv("POSTHOG_API_KEY"))
POSTHOG_API_KEY = os.getenv("POSTHOG_API_KEY", "")
POSTHOG_HOST = os.getenv("POSTHOG_HOST", "https://us.i.posthog.com")
POSTHOG_SALT = os.getenv("POSTHOG_SALT", "endurance-api")


def _anon_distinct_id(request: Request) -> str:
    seed = f"{request.headers.get('user-agent','')[:128]}|{request.client.host if request.client else ''}|{POSTHOG_SALT}"
    return hashlib.sha256(seed.encode()).hexdigest()[:32]


def _posthog_capture(event: str, properties: dict, distinct_id: str) -> None:
    if not POSTHOG_ENABLED:
        return
    payload = json.dumps({
        "api_key": POSTHOG_API_KEY,
        "event": event,
        "distinct_id": distinct_id,
        "properties": properties,
    }).encode()
    req = UrlRequest(
        f"{POSTHOG_HOST.rstrip('/')}/capture/",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=4) as resp:
            resp.read(1)
    except Exception:
        pass


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    started = asyncio.get_running_loop().time()
    path = request.url.path.rstrip("/") or "/"
    route_key = (request.method.upper(), path)
    paid = route_key in PAID_ENDPOINTS
    distinct_id = _anon_distinct_id(request)
    request_id = uuid4().hex

    if PAYMENT_ENFORCEMENT and paid:
        headers = {
            "WWW-Authenticate": f'MPP realm="{PUBLIC_ORIGIN_HOST}", origin="{PUBLIC_ORIGIN}", currency="USD", method="mpp"'
        }
        amount = PAID_ENDPOINTS[route_key]
        body = {
            "detail": "Payment Required",
            "price": {"mode": "fixed", "currency": "USD", "amount": f"{amount:.2f}"},
            "request_id": request_id,
        }
        response = JSONResponse(status_code=402, content=body, headers=headers)
        elapsed_ms = round((asyncio.get_running_loop().time() - started) * 1000, 1)
        if POSTHOG_ENABLED:
            response.background = BackgroundTask(
                _posthog_capture,
                "payment_challenge_issued",
                {
                    "route": path,
                    "method": request.method.upper(),
                    "amount": amount,
                    "currency": "USD",
                    "protocol": "mpp",
                    "status": 402,
                    "latency_ms": elapsed_ms,
                    "origin_host": PUBLIC_ORIGIN_HOST,
                    "request_id": request_id,
                },
                distinct_id,
            )
        return response

    response = await call_next(request)
    elapsed_ms = round((asyncio.get_running_loop().time() - started) * 1000, 1)
    if POSTHOG_ENABLED and request.url.path not in {"/openapi.json", "/docs", "/redoc"}:
        response.background = BackgroundTask(
            _posthog_capture,
            "api_request",
            {
                "route": path,
                "method": request.method.upper(),
                "status": response.status_code,
                "latency_ms": elapsed_ms,
                "paid": paid,
                "origin_host": PUBLIC_ORIGIN_HOST,
                "request_id": request_id,
            },
            distinct_id,
        )
        if response.status_code == 200 and paid:
            response.background = BackgroundTask(
                _posthog_capture,
                "payment_succeeded",
                {
                    "route": path,
                    "method": request.method.upper(),
                    "status": response.status_code,
                    "latency_ms": elapsed_ms,
                    "amount": PAID_ENDPOINTS[route_key],
                    "currency": "USD",
                    "origin_host": PUBLIC_ORIGIN_HOST,
                    "request_id": request_id,
                },
                distinct_id,
            )
    return response


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
app.include_router(favicon_router)


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

    for path, path_item in schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            operation["security"] = [] if (method.upper(), path) not in PAID_ENDPOINTS else [{"siwx": []}]
            _synthesize_request_body(operation)
            route_key = (method.upper(), path)
            if route_key in PAID_ENDPOINTS:
                amount = f"{PAID_ENDPOINTS[route_key]:.2f}"
                operation["x-payment-info"] = {
                    "price": {"mode": "fixed", "currency": "USD", "amount": amount},
                    "protocols": [
                        {"mpp": {"method": "mpp", "intent": f"{method.upper()} {path}", "currency": "USD", "realm": PUBLIC_ORIGIN_HOST, "origin": PUBLIC_ORIGIN}}
                    ],
                }
                operation.setdefault("responses", {})["402"] = {"description": "Payment Required"}

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/", include_in_schema=False)
def root():
    return {"name": "Endurance API", "version": "0.1.0", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}