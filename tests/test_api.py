"""Tests for endurance API."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_age_grade():
    r = client.post("/age-grade/calculate", json={
        "distance_m": 5000,
        "time_seconds": 1200,
        "age": 40,
        "sex": "M"
    })
    assert r.status_code == 200
    data = r.json()
    assert "age_grade_pct" in data
    assert 0 < data["age_grade_pct"] < 150


def test_vdot():
    r = client.post("/vdot/calculate", json={
        "distance_m": 5000,
        "time_seconds": 1200
    })
    assert r.status_code == 200
    data = r.json()
    assert "vdot" in data
    assert 30 < data["vdot"] < 85


def test_cat_ranking():
    r = client.post("/cat-ranking/calculate", json={
        "ftp_watts": 300,
        "weight_kg": 75,
        "sex": "M",
        "system": "usac"
    })
    assert r.status_code == 200
    data = r.json()
    assert "category" in data
    assert data["ftp_wkg"] == 4.0


def test_fina():
    r = client.post("/fina/calculate", json={
        "event": "100_free",
        "time_seconds": 55.0,
        "sex": "M"
    })
    assert r.status_code == 200
    data = r.json()
    assert "points" in data
    assert data["points"] > 0


def test_critical_power():
    r = client.post("/critical-power/calculate", json={
        "efforts": [
            {"duration_sec": 300, "power_watts": 350},
            {"duration_sec": 1200, "power_watts": 280}
        ]
    })
    assert r.status_code == 200
    data = r.json()
    assert "cp" in data
    assert data["cp"] > 0


def test_riegel():
    r = client.post("/riegel/predict", json={
        "known_distance_m": 5000,
        "known_time_sec": 1200,
        "target_distance_m": 10000
    })
    assert r.status_code == 200
    data = r.json()
    assert data["predicted_time_sec"] > 1200


def test_pace_convert():
    r = client.post("/pace/convert", json={
        "value": 5.0,
        "from_unit": "min_per_km",
        "to_unit": "min_per_mi"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["result"] > 5.0  # min/mi > min/km


def test_openapi_exists():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    assert spec["info"]["title"] == "Endurance API"
    assert "/age-grade/calculate" in spec["paths"]