"""Citizen Simple UI & Status Endpoint Tests.

Validates:
- GET /status endpoint response contract and state transitions (Safe, Watch, Warning, Danger)
- GPS proximity matching and district overrides
- Multilingual content support (English, Bengali, Hindi, Odia)
- Two-tier product routing (/ for Citizen Home, /console for Ops Dashboard)
- Advisory plain_instruction integration
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.contracts import CitizenStatusResponse

client = TestClient(app)


def test_status_endpoint_default_returns_danger():
    """Default location (South 24 Parganas in active storm path) must return Danger state."""
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    model = CitizenStatusResponse.model_validate(data)
    
    assert model.state == "Danger"
    assert model.color == "red"
    assert model.icon == "siren"
    assert model.headline == "TAKE ACTION NOW"
    assert model.district == "South 24 Parganas"
    assert model.max_failure_probability >= 0.70
    assert model.has_evacuation_action is True
    assert "Sagar Central" in model.plain_message
    assert len(model.emergency_contacts) >= 2
    assert model.shelter_info["distance_km"] > 0


def test_status_endpoint_state_transitions_by_district():
    """Validates all 4 states across known districts."""
    # 1. South 24 Parganas -> Danger
    r_danger = client.get("/status?district=South 24 Parganas")
    assert r_danger.status_code == 200
    assert r_danger.json()["state"] == "Danger"
    assert r_danger.json()["color"] == "red"

    # 2. Purba Medinipur -> Warning (30-70% failure probability)
    r_warning = client.get("/status?district=Purba Medinipur")
    assert r_warning.status_code == 200
    assert r_warning.json()["state"] == "Warning"
    assert r_warning.json()["color"] == "orange"
    assert r_warning.json()["icon"] == "triangle"
    assert r_warning.json()["headline"] == "GET READY"

    # 3. North 24 Parganas -> Watch (< 30% failure probability)
    r_watch = client.get("/status?district=North 24 Parganas")
    assert r_watch.status_code == 200
    assert r_watch.json()["state"] == "Watch"
    assert r_watch.json()["color"] == "yellow"
    assert r_watch.json()["icon"] == "eye"
    assert r_watch.json()["headline"] == "STAY ALERT"

    # 4. Kolkata -> Safe (0.0% failure probability)
    r_safe = client.get("/status?district=Kolkata")
    assert r_safe.status_code == 200
    assert r_safe.json()["state"] == "Safe"
    assert r_safe.json()["color"] == "green"
    assert r_safe.json()["icon"] == "check"
    assert r_safe.json()["headline"] == "SAFE"


def test_status_endpoint_gps_proximity_matching():
    """Validates GPS coordinates resolve to the nearest district."""
    # Near Sagar Island (South 24 Parganas)
    r_sagar = client.get("/status?lat=21.82&lon=88.22")
    assert r_sagar.status_code == 200
    assert r_sagar.json()["district"] == "South 24 Parganas"
    assert r_sagar.json()["state"] == "Danger"

    # Near Kolkata city center
    r_kolkata = client.get("/status?lat=22.56&lon=88.35")
    assert r_kolkata.status_code == 200
    assert r_kolkata.json()["district"] == "Kolkata"
    assert r_kolkata.json()["state"] == "Safe"

    # Near Digha coast (Purba Medinipur)
    r_digha = client.get("/status?lat=21.63&lon=87.51")
    assert r_digha.status_code == 200
    assert r_digha.json()["district"] == "Purba Medinipur"
    assert r_digha.json()["state"] == "Warning"


def test_status_endpoint_multilingual():
    """Validates multilingual translation support for bn, hi, or."""
    # Bengali (bn)
    r_bn = client.get("/status?district=South 24 Parganas&lang=bn")
    assert r_bn.status_code == 200
    d_bn = r_bn.json()
    assert d_bn["headline"] == "অবিলম্বে পদক্ষেপ নিন"
    assert "সাগর সেন্ট্রাল" in d_bn["plain_message"] or "সাগর সেন্ট্রাল" in d_bn["plain_instruction"]

    # Hindi (hi)
    r_hi = client.get("/status?district=South 24 Parganas&lang=hi")
    assert r_hi.status_code == 200
    d_hi = r_hi.json()
    assert d_hi["headline"] == "तुरंत कार्रवाई करें"
    assert "सागर सेंट्रल" in d_hi["plain_message"]

    # Odia (or)
    r_or = client.get("/status?district=South 24 Parganas&lang=or")
    assert r_or.status_code == 200
    d_or = r_or.json()
    assert d_or["headline"] == "ତୁରନ୍ତ ପଦକ୍ଷେପ ନିଅନ୍ତୁ"
    assert "ସାଗର ସେଣ୍ଟ୍ରାଲ" in d_or["plain_message"]


def test_two_tier_routing():
    """Validates / and /citizen serve Citizen Home, and /console serves Ops Console."""
    r_root = client.get("/")
    assert r_root.status_code == 200

    r_citizen = client.get("/citizen")
    assert r_citizen.status_code == 200

    r_console = client.get("/console")
    assert r_console.status_code == 200
    assert "Aegis-APAC" in r_console.text
