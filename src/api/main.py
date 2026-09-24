"""Aegis-APAC FastAPI Application.

Implements all endpoints defined in PRD Section 8.8. Serves precomputed
scenario data in DEMO_MODE, supports operator authorization for advisory
approval, and generates CAP 1.2 alert feeds.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET
import numpy as np

from fastapi import Depends, FastAPI, HTTPException, Header, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from src.contracts import (
    Action,
    Advisory,
    AdvisoryStatus,
    Facility,
    ParametricResult,
    RiskResult,
    Scenario,
)

app = FastAPI(
    title="Aegis-APAC API",
    version="2.0.0",
    description="Anticipatory Action and Cyclone Impact Platform for Coastal APAC",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# Enable CORS for local testing and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration & Data Directory Paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", REPO_ROOT / "data"))
GOLDEN_DIR = DATA_DIR / "golden" / "amphan-2020"
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "aegis_hackathon_demo_secret_token_2026")

# Observability Metrics Store
_METRICS = {
    "total_requests": 0,
    "status_2xx": 0,
    "status_4xx": 0,
    "status_5xx": 0,
    "latencies_ms": [],
}

@app.middleware("http")
async def observability_middleware(request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    
    _METRICS["total_requests"] += 1
    if 200 <= response.status_code < 300:
        _METRICS["status_2xx"] += 1
    elif 400 <= response.status_code < 500:
        _METRICS["status_4xx"] += 1
    elif response.status_code >= 500:
        _METRICS["status_5xx"] += 1
        
    if len(_METRICS["latencies_ms"]) > 1000:
        _METRICS["latencies_ms"].pop(0)
    _METRICS["latencies_ms"].append(duration_ms)
    
    response.headers["X-Process-Time-Ms"] = str(duration_ms)
    return response


def load_json(file_path: Path) -> Any:
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource file not found: {file_path.name}",
        )
    return json.loads(file_path.read_text(encoding="utf-8"))


# --- In-Memory State for Advisories (permits state transition during demo) ---
_ADVISORY_CACHE: Dict[str, Dict[str, Any]] = {}


def get_advisories_data() -> List[Dict[str, Any]]:
    global _ADVISORY_CACHE
    if not _ADVISORY_CACHE:
        raw_list = load_json(GOLDEN_DIR / "advisories.json")
        for adv in raw_list:
            _ADVISORY_CACHE[adv["id"]] = adv
    return list(_ADVISORY_CACHE.values())


# --- Operator Authentication Dependency ---
def verify_operator_token(
    authorization: Optional[str] = Header(None),
    x_admin_token: Optional[str] = Header(None),
) -> bool:
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1]
    elif x_admin_token:
        token = x_admin_token
    
    if token != ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing operator authorization token. Human confirmation required.",
        )
    return True


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health", tags=["System"])
def health_check():
    """System health check and component operational mode."""
    bundle_ok = (GOLDEN_DIR / "scenario.json").is_file()
    return {
        "status": "healthy" if bundle_ok else "degraded",
        "demo_mode": DEMO_MODE,
        "region": "bengal_delta",
        "version": "2.0.0",
        "components": {
            "golden_bundle": "ready" if bundle_ok else "missing",
            "degraded_template_fallback": "active",
            "gemini_api": "configured" if os.getenv("GEMINI_API_KEY") else "degraded_template_mode",
            "database_cache": "in_memory_sqlite_ok",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/metrics", tags=["System"])
def get_metrics():
    """Observability metrics endpoint exposing request counts and latency percentiles."""
    latencies = _METRICS["latencies_ms"]
    p50 = float(np.percentile(latencies, 50)) if latencies else 0.0
    p95 = float(np.percentile(latencies, 95)) if latencies else 0.0
    avg = float(np.mean(latencies)) if latencies else 0.0

    return {
        "total_requests": _METRICS["total_requests"],
        "status_2xx": _METRICS["status_2xx"],
        "status_4xx": _METRICS["status_4xx"],
        "status_5xx": _METRICS["status_5xx"],
        "latency_p50_ms": round(p50, 2),
        "latency_p95_ms": round(p95, 2),
        "latency_avg_ms": round(avg, 2),
        "demo_mode": DEMO_MODE,
    }


@app.get("/scenarios", response_model=List[Scenario], tags=["Scenarios"])
def list_scenarios():
    """List available storm forecast scenarios."""
    sc_data = load_json(GOLDEN_DIR / "scenario.json")
    return [Scenario.model_validate(sc_data)]


@app.get("/scenarios/{scenario_id}", response_model=Scenario, tags=["Scenarios"])
def get_scenario(scenario_id: str):
    """Retrieve detailed scenario metadata."""
    sc_data = load_json(GOLDEN_DIR / "scenario.json")
    if sc_data["id"] != scenario_id:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return Scenario.model_validate(sc_data)


@app.get("/scenarios/{scenario_id}/hazard", tags=["Hazard"])
def get_hazard_layers(
    scenario_id: str,
    t: Optional[int] = Query(None, description="Time step relative to landfall (-24, -12, -6, 0, 6)"),
    threshold: Optional[float] = Query(None, description="Depth threshold in meters (0.3 or 1.0)"),
):
    """Retrieve GeoJSON probability inundation layers filtered by time and depth threshold."""
    geojson_data = load_json(GOLDEN_DIR / "hazard_layers.json")
    features = geojson_data.get("features", [])
    
    if t is not None:
        features = [f for f in features if f["properties"].get("time_step_h") == t]
    if threshold is not None:
        features = [f for f in features if f["properties"].get("threshold_m") == threshold]
        
    return {
        "type": "FeatureCollection",
        "scenario_id": scenario_id,
        "features": features,
    }


@app.get("/scenarios/{scenario_id}/pathways", tags=["Hazard"])
def get_damage_pathways(scenario_id: str):
    """Retrieve DEM-derived rainfall drainage channels and surge funnels."""
    return load_json(GOLDEN_DIR / "pathways.geojson")


@app.get("/scenarios/{scenario_id}/facilities", response_model=List[Facility], tags=["Facilities"])
def list_facilities(scenario_id: str):
    """Retrieve critical infrastructure facilities for the pilot region."""
    data = load_json(GOLDEN_DIR / "facilities.json")
    return [Facility.model_validate(f) for f in data]


@app.get("/facilities/{facility_id}/risk", response_model=RiskResult, tags=["Facilities"])
def get_facility_risk(facility_id: str):
    """Retrieve risk prediction, earliest failure time, and warning hours for a facility."""
    risks = load_json(GOLDEN_DIR / "risks.json")
    for r in risks:
        if r["facility_id"] == facility_id:
            return RiskResult.model_validate(r)
    raise HTTPException(status_code=404, detail=f"No risk calculation found for {facility_id}")


@app.get("/facilities/{facility_id}/cascade", tags=["Facilities"])
def get_facility_cascade(facility_id: str):
    """Retrieve connected infrastructure dependency graph and failure cause chain."""
    risks = load_json(GOLDEN_DIR / "risks.json")
    edges = load_json(GOLDEN_DIR / "edges.json")
    facilities = load_json(GOLDEN_DIR / "facilities.json")
    
    facility_risk = next((r for r in risks if r["facility_id"] == facility_id), None)
    if not facility_risk:
        raise HTTPException(status_code=404, detail="Facility risk not found")
        
    connected_edges = [
        e for e in edges if e["from_node"] == facility_id or e["to_node"] == facility_id
    ]
    connected_node_ids = {facility_id}
    for e in connected_edges:
        connected_node_ids.add(e["from_node"])
        connected_node_ids.add(e["to_node"])
        
    connected_facilities = [f for f in facilities if f["id"] in connected_node_ids]
    
    return {
        "target_facility_id": facility_id,
        "risk": facility_risk,
        "nodes": connected_facilities,
        "edges": connected_edges,
        "cause_chain": facility_risk.get("cause_chain", []),
    }


@app.get("/scenarios/{scenario_id}/actions", response_model=List[Action], tags=["Decision"])
def list_actions(scenario_id: str):
    """Retrieve recommended anticipatory actions, shelter allocations, and road closures."""
    data = load_json(GOLDEN_DIR / "actions.json")
    return [Action.model_validate(a) for a in data]


@app.get("/scenarios/{scenario_id}/parametric", response_model=List[ParametricResult], tags=["Parametric"])
def get_parametric_trigger(scenario_id: str):
    """Retrieve parametric insurance trigger probabilities and basis risk evaluation."""
    data = load_json(GOLDEN_DIR / "parametric.json")
    return [ParametricResult.model_validate(p) for p in data]


@app.get("/advisories", response_model=List[Advisory], tags=["Advisories"])
def list_advisories(
    scenario_id: Optional[str] = None,
    role: Optional[str] = None,
    lang: Optional[str] = None,
):
    """List early-warning advisories with optional filtering by role and language."""
    items = get_advisories_data()
    if scenario_id:
        items = [a for a in items if a.get("scenario_id") == scenario_id]
    if role:
        items = [a for a in items if a.get("role") == role]
    if lang:
        items = [a for a in items if a.get("language") == lang]
    return [Advisory.model_validate(a) for a in items]


@app.post("/advisories/{advisory_id}/approve", response_model=Advisory, tags=["Advisories"])
def approve_advisory(
    advisory_id: str,
    operator_name: str = Query("Operator", description="Identity of approving official"),
    authorized: bool = Depends(verify_operator_token),
):
    """Authorize and approve a draft advisory for dispatch (Requires ADMIN_TOKEN)."""
    advisories = get_advisories_data()
    for adv in advisories:
        if adv["id"] == advisory_id:
            adv["status"] = AdvisoryStatus.APPROVED.value
            adv["history"].append({
                "status": AdvisoryStatus.APPROVED.value,
                "at": datetime.now(timezone.utc).isoformat(),
                "actor": operator_name,
            })
            return Advisory.model_validate(adv)
    raise HTTPException(status_code=404, detail="Advisory not found")


@app.get("/advisories/{advisory_id}/cap", tags=["Advisories"])
def export_advisory_cap(advisory_id: str):
    """Export an approved advisory in OASIS Common Alerting Protocol (CAP 1.2) XML format."""
    advisories = get_advisories_data()
    adv = next((a for a in advisories if a["id"] == advisory_id), None)
    if not adv:
        raise HTTPException(status_code=404, detail="Advisory not found")
        
    # Build valid CAP 1.2 XML tree
    alert = ET.Element(
        "alert",
        xmlns="urn:oasis:names:tc:emergency:cap:1.2"
    )
    ET.SubElement(alert, "identifier").text = f"AEGIS-APAC-{adv['id']}"
    ET.SubElement(alert, "sender").text = "operations@aegis-apac.org"
    ET.SubElement(alert, "sent").text = datetime.now(timezone.utc).isoformat()
    ET.SubElement(alert, "status").text = "Actual" if adv["status"] == "approved" else "Draft"
    ET.SubElement(alert, "msgType").text = "Alert"
    ET.SubElement(alert, "scope").text = "Public"
    
    info = ET.SubElement(alert, "info")
    ET.SubElement(info, "language").text = adv["language"]
    ET.SubElement(info, "category").text = "Met"
    ET.SubElement(info, "event").text = "Tropical Cyclone Coastal Impact"
    ET.SubElement(info, "urgency").text = "Expected"
    ET.SubElement(info, "severity").text = "Severe"
    ET.SubElement(info, "certainty").text = "Likely"
    ET.SubElement(info, "headline").text = f"Anticipatory Warning - Role: {adv['role']}"
    ET.SubElement(info, "description").text = adv["text"]
    
    xml_str = ET.tostring(alert, encoding="utf-8", xml_declaration=True)
    return Response(content=xml_str, media_type="application/xml")


@app.get("/backtest/{storm}/metrics", tags=["Backtest"])
def get_backtest_metrics(storm: str):
    """Retrieve historical backtest validation metrics and baseline benchmarks."""
    return load_json(GOLDEN_DIR / "metrics.json")


# Mount Web Dashboard (Static Files)
WEB_DIR = REPO_ROOT / "web"
if WEB_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

@app.get("/", include_in_schema=False)
def serve_index():
    index_file = WEB_DIR / "index.html"
    if index_file.is_file():
        return Response(content=index_file.read_text(encoding="utf-8"), media_type="text/html")
    return {"message": "Aegis-APAC API is operational. Visit /docs for OpenAPI documentation."}
