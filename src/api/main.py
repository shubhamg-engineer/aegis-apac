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
    CitizenStatusResponse,
    Facility,
    ParametricResult,
    RiskResult,
    Scenario,
)
from src.ingest.gee import EarthEngineIngest

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
    gee_diag = EarthEngineIngest().check_connection()
    return {
        "status": "healthy" if bundle_ok else "degraded",
        "demo_mode": DEMO_MODE,
        "region": "bengal_delta",
        "version": "2.0.0",
        "components": {
            "golden_bundle": "ready" if bundle_ok else "missing",
            "degraded_template_fallback": "active",
            "gemini_api": "configured" if os.getenv("GEMINI_API_KEY") else "degraded_template_mode",
            "earth_engine": gee_diag["mode"],
            "database_cache": "in_memory_sqlite_ok",
        },
        "earth_engine": {
            "mode": gee_diag["mode"],
            "authenticated": gee_diag["initialized"],
            "auth_method": gee_diag["auth_method"],
            "project_id": gee_diag["project_id"],
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/gee/status", tags=["Earth Engine"])
def get_gee_status():
    """Return status of Google Earth Engine batch ingestion readiness and datasets."""
    return EarthEngineIngest().check_connection()


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


# ============================================================================
# Citizen Home Status & Presentation Layer (Spec Section 7 & 8)
# ============================================================================

DISTRICT_CONFIG = {
    "South 24 Parganas": {
        "lat": 21.80,
        "lon": 88.20,
        "shelter": {
            "name": "Sagar Central Multi-purpose Shelter",
            "distance_km": 1.4,
            "capacity": 1500,
            "address": "Sagar Island Block, South 24 Parganas",
        },
    },
    "Purba Medinipur": {
        "lat": 21.90,
        "lon": 87.80,
        "shelter": {
            "name": "Digha Coastal Cyclone Shelter",
            "distance_km": 2.1,
            "capacity": 1200,
            "address": "Digha Coastal Sector, Purba Medinipur",
        },
    },
    "North 24 Parganas": {
        "lat": 22.65,
        "lon": 88.55,
        "shelter": {
            "name": "Hingalganj Multi-purpose Shelter",
            "distance_km": 3.8,
            "capacity": 800,
            "address": "Hingalganj Block, North 24 Parganas",
        },
    },
    "Kolkata": {
        "lat": 22.57,
        "lon": 88.36,
        "shelter": {
            "name": "Kolkata Central Emergency Relief Center",
            "distance_km": 5.0,
            "capacity": 2000,
            "address": "BBD Bagh, Kolkata",
        },
    },
}

LOCALIZED_CONTENT = {
    "en": {
        "Safe": {
            "headline": "SAFE",
            "message": "No cyclone threat in your area right now.",
            "instruction": "Continue monitoring local weather updates.",
            "actions": [
                "No immediate precautionary action required",
                "Ensure emergency contacts are saved on your phone",
                "Check periodic forecasts if traveling towards coastal districts",
            ],
        },
        "Watch": {
            "headline": "STAY ALERT",
            "message": "A storm is forming. No action needed yet. We'll notify you if that changes.",
            "instruction": "Monitor weather advisories and verify emergency supplies.",
            "actions": [
                "Track official storm bulletins every 6 hours",
                "Inspect home roof, drainage, and backup batteries",
                "Keep emergency contact numbers handy",
            ],
        },
        "Warning": {
            "headline": "GET READY",
            "message": "Flooding possible in your area within 24 hours. Prepare to move if told to.",
            "instruction": "Prepare essential emergency kit and identify nearest shelter.",
            "actions": [
                "Pack drinking water, essential medicines, and waterproof bags for documents",
                "Charge phones, torches, and power banks",
                "Prepare elderly, children, and livestock for possible relocation",
            ],
        },
        "Danger": {
            "headline": "TAKE ACTION NOW",
            "message": "Evacuate to Sagar Central Shelter before 4:00 AM.",
            "instruction": "Move to Sagar Central Shelter before 4:00 AM. Avoid flooded roads.",
            "actions": [
                "Evacuate immediately to Sagar Central Multi-purpose Shelter before 4:00 AM",
                "Avoid NH-12 coastal causeway (critical flood risk)",
                "Turn off main gas and power switches before leaving home",
            ],
        },
    },
    "bn": {
        "Safe": {
            "headline": "নিরাপদ",
            "message": "আপনার এলাকায় বর্তমানে কোনো ঘূর্ণিঝড়ের আশঙ্কা নেই।",
            "instruction": "স্বাভাবিক কাজকর্ম চালিয়ে যান ও আবহাওয়া খবরে নজর রাখুন।",
            "actions": [
                "আপাতত কোনো পদক্ষেপ নেওয়ার প্রয়োজন নেই",
                "ফোনে জরুরি হেল্পলাইন নম্বর সেভ রাখুন",
                "উপকূলবর্তী এলাকায় ভ্রমণের ক্ষেত্রে আবহাওয়ার পূর্বাভাস দেখুন",
            ],
        },
        "Watch": {
            "headline": "সতর্ক থাকুন",
            "message": "একটি ঝড় ঘনীভূত হচ্ছে। এখনই পদক্ষেপ নেওয়ার প্রয়োজন নেই। পরিস্থিতি বদলালে জানানো হবে।",
            "instruction": "সরকারি বুলেটিনে নজর রাখুন এবং প্রস্তুতি যাচাই করে রাখুন।",
            "actions": [
                "প্রতি ৬ ঘণ্টা অন্তর সরকারি আবহাওয়া বুলেটিন শুনুন",
                "বাড়ির ছাদ, নিকাশি নালা এবং ব্যাটারি প্রস্তুত রাখুন",
                "জরুরি হেল্পলাইন নম্বর হাতের কাছে রাখুন",
            ],
        },
        "Warning": {
            "headline": "প্রস্তুত থাকুন",
            "message": "আগামী ২৪ ঘণ্টার মধ্যে আপনার এলাকায় প্লাবনের আশঙ্কা রয়েছে। নির্দেশ পেলে নিরাপদ আশ্রয়ে যাওয়ার প্রস্তুতি নিন।",
            "instruction": "জরুরি সরঞ্জাম প্রস্তুত রাখুন এবং নিকটবর্তী আশ্রয়কেন্দ্র চিহ্নিত করুন।",
            "actions": [
                "পানীয় জল, প্রয়োজনীয় ওষুধ ও নথিপত্র ওয়াটারপ্রুফ ব্যাগে গুছিয়ে রাখুন",
                "মোবাইল ফোন ও টর্চ সম্পূর্ণ চার্জ দিয়ে রাখুন",
                "প্রবীণ ও শিশুদের দ্রুত নিরাপদ স্থানে নিয়ে যাওয়ার জন্য প্রস্তুত থাকুন",
            ],
        },
        "Danger": {
            "headline": "অবিলম্বে পদক্ষেপ নিন",
            "message": "ভোর ৪:০০ টার মধ্যে সাগর সেন্ট্রাল সাইক্লোন শেল্টারে চলে যান।",
            "instruction": "প্লাবিত রাস্তা এড়িয়ে ভোর ০৪:০০ টার মধ্যে সাগর সেন্ট্রাল শেল্টারে চলে যান।",
            "actions": [
                "ভোর ৪:০০ টার মধ্যে সাগর সেন্ট্রাল বহুমুখী ঘূর্ণিঝড় আশ্রয়কেন্দ্রে আশ্রয় নিন",
                "এনএইচ-১২ উপকূলবর্তী কজওয়ে এড়িয়ে চলুন (জলমগ্ন হওয়ার ঝুঁকি)",
                "বাড়ি ছাড়ার আগে গ্যাস ও বিদ্যুতের মেইন সুইচ বন্ধ করুন",
            ],
        },
    },
    "hi": {
        "Safe": {
            "headline": "सुरक्षित",
            "message": "वर्तमान में आपके क्षेत्र में चक्रवात का कोई खतरा नहीं है।",
            "instruction": "सामान्य कार्य जारी रखें और मौसम अपडेट पर ध्यान दें।",
            "actions": [
                "वर्तमान में किसी आपातकालीन कार्रवाई की आवश्यकता नहीं है",
                "फोन में आपदा संपर्क नंबर सहेज कर रखें",
                "तटीय क्षेत्रों की यात्रा करते समय मौसम की जानकारी अवश्य लें",
            ],
        },
        "Watch": {
            "headline": "सतर्क रहें",
            "message": "एक तूफान बन रहा है। अभी किसी कार्रवाई की आवश्यकता नहीं है। बदलाव होने पर सूचित किया जाएगा।",
            "instruction": "आधिकारिक मौसम बुलेटिन सुनते रहें और आवश्यक वस्तुओं की जांच करें।",
            "actions": [
                "हर 6 घंटे में आधिकारिक मौसम अपडेट देखें",
                "घर की छत, जल निकासी और बैटरी की स्थिति जांचें",
                "आपातकालीन नंबर तैयार रखें",
            ],
        },
        "Warning": {
            "headline": "तैयार रहें",
            "message": "अगले 24 घंटों में आपके क्षेत्र में बाढ़ की संभावना है। निर्देश मिलने पर सुरक्षित स्थान पर जाने के लिए तैयार रहें।",
            "instruction": "आपातकालीन किट तैयार रखें और निकटतम चक्रवात आश्रय की पहचान करें।",
            "actions": [
                "पीने का पानी, आवश्यक दवाएं और महत्वपूर्ण दस्तावेज सुरक्षित बैग में रखें",
                "मोबाइल और टॉर्च को पूरा चार्ज रखें",
                "बुजुर्गों, बच्चों और पशुओं को सुरक्षित स्थान पर ले जाने की तैयारी रखें",
            ],
        },
        "Danger": {
            "headline": "तुरंत कार्रवाई करें",
            "message": "सुबह 4:00 बजे से पहले सागर सेंट्रल चक्रवात आश्रय में जाएं।",
            "instruction": "जलमग्न सड़कों से बचें और सुबह 04:00 बजे से पहले सागर सेंट्रल शेल्टर में जाएं।",
            "actions": [
                "सुबह 4:00 बजे से पहले सागर सेंट्रल बहुउद्देशीय आश्रय में शरण लें",
                "NH-12 तटीय मार्ग से बचें (भारी जलभराव का खतरा)",
                "घर से निकलते समय गैस सिलेंडर और मुख्य बिजली स्विच बंद करें",
            ],
        },
    },
    "or": {
        "Safe": {
            "headline": "ସୁରକ୍ଷିତ",
            "message": "ବର୍ତ୍ତମାନ ଆପଣଙ୍କ ଅଞ୍ଚଳରେ କୌଣସି ବାତ୍ୟା ଆଶଙ୍କା ନାହିଁ।",
            "instruction": "ସ୍ୱାଭାବିକ କାର୍ଯ୍ୟ ଜାରି ରଖନ୍ତୁ ଏବଂ ପାଣିପାଗ ଖବର ଉପରେ ନଜର ରଖନ୍ତୁ।",
            "actions": [
                "କୌଣସି ପଦକ୍ଷେପ ନେବାର ଆବଶ୍ୟକତା ନାହିଁ",
                "ଫୋନ୍‌ରେ ଜରୁରୀକାଳୀନ ହେଲ୍ପଲାଇନ୍ ନମ୍ବର ସାଇତି ରଖନ୍ତୁ",
                "ଉପକୂଳ ଯାତ୍ରା ପୂର୍ବରୁ ପାଣିପାଗ ସତର୍କତା ଯାଞ୍ଚ କରନ୍ତୁ",
            ],
        },
        "Watch": {
            "headline": "ସତର୍କ ରୁହନ୍ତୁ",
            "message": "ଏକ ବାତ୍ୟା ସୃଷ୍ଟି ହେଉଛି। ଏବେ କୌଣସି ପଦକ୍ଷେପ ନେବା ଆବଶ୍ୟକ ନାହିଁ। ପରିବର୍ତ୍ତନ ହେଲେ ଜଣାଇ ଦିଆଯିବ।",
            "instruction": "ସରକାରୀ ବୁଲେଟିନ୍ ଉପରେ ନଜର ରଖନ୍ତୁ ଏବଂ ପ୍ରସ୍ତୁତି ଯାଞ୍ଚ କରନ୍ତୁ।",
            "actions": [
                "ପ୍ରତି ୬ ଘଣ୍ଟାରେ ସରକାରୀ ପାଣିପାଗ ସୂଚନା ଶୁଣନ୍ତୁ",
                "ଘର ଛାତ ଏବଂ ଜଳ ନିଷ୍କାସନ ବ୍ୟବସ୍ଥା ଯାଞ୍ଚ କରନ୍ତୁ",
                "ଆପାତକାଳୀନ ସମ୍ପର୍କ ନମ୍ବର ପାଖରେ ରଖନ୍ତୁ",
            ],
        },
        "Warning": {
            "headline": "ପ୍ରସ୍ତୁତ ରୁହନ୍ତୁ",
            "message": "ଆଗାମୀ ୨୪ ଘଣ୍ଟା ମଧ୍ୟରେ ଆପଣଙ୍କ ଅଞ୍ଚଳରେ ବନ୍ୟା ଆଶଙ୍କା ରହିଛି। ନିର୍ଦ୍ଦେଶ ମିଳିଲେ ସ୍ଥାନାନ୍ତର ପାଇଁ ପ୍ରସ୍ତୁତ ରୁହନ୍ତୁ।",
            "instruction": "ଜରୁରୀ ସାମଗ୍ରୀ ପ୍ରସ୍ତୁତ ରଖନ୍ତୁ ଏବଂ ନିକଟସ୍ଥ ବାତ୍ୟା ଆଶ୍ରୟସ୍ଥଳୀ ଚିହ୍ନଟ କରନ୍ତୁ।",
            "actions": [
                "ପାନୀୟ ଜଳ, ଔଷଧ ଓ ଗୁରୁତ୍ୱପୂର୍ଣ୍ଣ କାଗଜପତ୍ର ସୁରକ୍ଷିତ ବ୍ୟାଗରେ ରଖନ୍ତୁ",
                "ମୋବାଇଲ୍ ଓ ଟର୍ଚ୍ଚ ସମ୍ପୂର୍ଣ୍ଣ ଚାର୍ଜ ରଖନ୍ତୁ",
                "ବୃଦ୍ଧ ଓ ପିଲାମାନଙ୍କୁ ସୁରକ୍ଷିତ ସ୍ଥାନକୁ ନେବା ପାଇଁ ପ୍ରସ୍ତୁତ ରୁହନ୍ତୁ",
            ],
        },
        "Danger": {
            "headline": "ତୁରନ୍ତ ପଦକ୍ଷେପ ନିଅନ୍ତୁ",
            "message": "ସକାଳ ୪:୦୦ ପୂର୍ବରୁ ସାଗର ସେଣ୍ଟ୍ରାଲ ବାତ୍ୟା ଆଶ୍ରୟସ୍ଥଳୀକୁ ଯାଆନ୍ତୁ।",
            "instruction": "ବନ୍ୟା ପ୍ରଭାବିତ ରାସ୍ତା ଛାଡ଼ି ସକାଳ ୦୪:୦୦ ପୂର୍ବରୁ ସାଗର ସେଣ୍ଟ୍ରାଲ ଆଶ୍ରୟକୁ ଯାଆନ୍ତୁ।",
            "actions": [
                "ସକାଳ ୪:୦୦ ପୂର୍ବରୁ ସାଗର ସେଣ୍ଟ୍ରାଲ ବାତ୍ୟା ଆଶ୍ରୟସ୍ଥଳୀକୁ ଯାଆନ୍ତୁ",
                "ଏନ୍‌ଏଚ୍-୧୨ ଉପକୂଳ ରାସ୍ତା ବ୍ୟବହାର କରନ୍ତୁ ନାହିଁ",
                "ଘର ଛାଡ଼ିବା ପୂର୍ବରୁ ମୁଖ୍ୟ ବିଦ୍ୟୁତ ସୁଇଚ୍ ବନ୍ଦ କରନ୍ତୁ",
            ],
        },
    },
}


def resolve_district(lat: Optional[float], lon: Optional[float], district: Optional[str]) -> str:
    if district:
        d_lower = district.strip().lower()
        for k in DISTRICT_CONFIG:
            if k.lower() in d_lower or d_lower in k.lower():
                return k
        if "sagar" in d_lower or "sundarban" in d_lower or "south" in d_lower:
            return "South 24 Parganas"
        if "digha" in d_lower or "purba" in d_lower or "medinipur" in d_lower or "midnapore" in d_lower:
            return "Purba Medinipur"
        if "north" in d_lower:
            return "North 24 Parganas"
        if "kolkata" in d_lower or "calcutta" in d_lower or "howrah" in d_lower:
            return "Kolkata"

    if lat is not None and lon is not None:
        best_dist = None
        best_dname = "South 24 Parganas"
        for name, meta in DISTRICT_CONFIG.items():
            dist_deg = ((meta["lat"] - lat) ** 2 + (meta["lon"] - lon) ** 2) ** 0.5
            if best_dist is None or dist_deg < best_dist:
                best_dist = dist_deg
                best_dname = name
        return best_dname

    return "South 24 Parganas"


@app.get("/status", response_model=CitizenStatusResponse, tags=["Citizen"])
def get_citizen_status(
    lat: Optional[float] = Query(None, description="Citizen GPS latitude"),
    lon: Optional[float] = Query(None, description="Citizen GPS longitude"),
    district: Optional[str] = Query(None, description="District name"),
    lang: Optional[str] = Query("en", description="Language code: en, bn, hi, or"),
):
    """Aggregate risk, actions, and advisories into a single-glance citizen status."""
    matched_district = resolve_district(lat, lon, district)
    meta = DISTRICT_CONFIG.get(matched_district, DISTRICT_CONFIG["South 24 Parganas"])

    # Load underlying precomputed golden datasets
    risks_data = load_json(GOLDEN_DIR / "risks.json") if (GOLDEN_DIR / "risks.json").is_file() else []
    actions_data = load_json(GOLDEN_DIR / "actions.json") if (GOLDEN_DIR / "actions.json").is_file() else []
    params_data = load_json(GOLDEN_DIR / "parametric.json") if (GOLDEN_DIR / "parametric.json").is_file() else []
    advisories = get_advisories_data()

    # Determine probabilities & evacuation action based on district
    if matched_district == "South 24 Parganas":
        max_failure_prob = max((r.get("failure_probability", 0.0) for r in risks_data), default=0.88)
        has_evac = any(a.get("type") == "evacuate" for a in actions_data)
        trigger_prob = next(
            (p.get("trigger_probability", 0.82) for p in params_data if p.get("district") == "South 24 Parganas"),
            0.82,
        )
    elif matched_district == "Purba Medinipur":
        max_failure_prob = 0.52
        has_evac = False
        trigger_prob = 0.45
    elif matched_district == "North 24 Parganas":
        max_failure_prob = 0.18
        has_evac = False
        trigger_prob = 0.15
    else:  # Kolkata or safe zone
        max_failure_prob = 0.0
        has_evac = False
        trigger_prob = 0.0

    # Rule (Gaps Spec Section 7):
    # Safe if 0% / no threat
    # Watch if < 30%
    # Warning if 30-70%
    # Danger if > 70% OR approved evacuation Action exists
    if max_failure_prob == 0.0:
        state = "Safe"
        color = "green"
        icon = "check"
    elif max_failure_prob < 0.30:
        state = "Watch"
        color = "yellow"
        icon = "eye"
    elif max_failure_prob <= 0.70 and not has_evac:
        state = "Warning"
        color = "orange"
        icon = "triangle"
    else:
        state = "Danger"
        color = "red"
        icon = "siren"

    # Select language bundle (fallback to en)
    language = (lang or "en").lower()
    if language not in LOCALIZED_CONTENT:
        language = "en"
    content = dict(LOCALIZED_CONTENT[language][state])

    # Find relevant advisory if danger/warning
    advisory_id = None
    advisory_text = None
    if state in ("Danger", "Warning"):
        citizen_adv = next((a for a in advisories if a.get("language") == language and a.get("role") in ("citizens", "collector")), None)
        if citizen_adv:
            advisory_id = citizen_adv.get("id")
            advisory_text = citizen_adv.get("text")
            if state == "Danger" and citizen_adv.get("plain_instruction"):
                content["instruction"] = citizen_adv["plain_instruction"]
                content["message"] = citizen_adv["plain_instruction"]
        else:
            # Fallback to English advisory for reference text/ID if needed, but preserve localized content message
            fallback_adv = next((a for a in advisories if a.get("role") in ("citizens", "collector")), None)
            if fallback_adv:
                advisory_id = fallback_adv.get("id")
                advisory_text = fallback_adv.get("text")

    emergency_contacts = [
        {"name": "District Disaster Helpline", "phone": "1077"},
        {"name": "National Emergency Services", "phone": "112"},
        {"name": "Medical Emergency (Ambulance)", "phone": "108"},
    ]

    return CitizenStatusResponse(
        state=state,
        color=color,
        icon=icon,
        headline=content["headline"],
        plain_message=content["message"],
        plain_instruction=content["instruction"],
        district=matched_district,
        max_failure_probability=round(max_failure_prob, 2),
        parametric_trigger_probability=round(trigger_prob, 2),
        has_evacuation_action=has_evac,
        shelter_info=meta["shelter"],
        emergency_contacts=emergency_contacts,
        actions=content["actions"],
        advisory_id=advisory_id,
        advisory_text=advisory_text,
        last_updated=datetime.now(timezone.utc).isoformat(),
        language=language,
    )


# ============================================================================
# Web Dashboard & Static Routing (Product Structure: Two Tiers)
# ============================================================================
WEB_DIR = REPO_ROOT / "web"
if WEB_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/console", include_in_schema=False)
def serve_console():
    """Serve existing Ops Console for officials, disaster analysts, and judges."""
    index_file = WEB_DIR / "index.html"
    if index_file.is_file():
        return Response(content=index_file.read_text(encoding="utf-8"), media_type="text/html")
    return {"message": "Ops Console file not found"}


@app.get("/citizen", include_in_schema=False)
@app.get("/", include_in_schema=False)
def serve_citizen_home():
    """Serve Citizen Home as the primary landing page (Simple Mode UI)."""
    citizen_file = WEB_DIR / "citizen.html"
    if citizen_file.is_file():
        return Response(content=citizen_file.read_text(encoding="utf-8"), media_type="text/html")
    index_file = WEB_DIR / "index.html"
    if index_file.is_file():
        return Response(content=index_file.read_text(encoding="utf-8"), media_type="text/html")
    return {"message": "Aegis-APAC API is operational. Visit /docs for OpenAPI documentation."}


@app.get("/{file_name:path}", include_in_schema=False)
def serve_root_static(file_name: str):
    """Serve static assets requested from root (e.g. app.js, style.css, citizen.js)."""
    target = WEB_DIR / file_name
    if target.is_file() and not file_name.startswith(".."):
        media_type = "text/plain"
        if file_name.endswith(".html"):
            media_type = "text/html"
        elif file_name.endswith(".js"):
            media_type = "application/javascript"
        elif file_name.endswith(".css"):
            media_type = "text/css"
        elif file_name.endswith(".json") or file_name.endswith(".geojson"):
            media_type = "application/json"
        elif file_name.endswith(".png"):
            media_type = "image/png"
        elif file_name.endswith(".svg"):
            media_type = "image/svg+xml"
        return Response(content=target.read_bytes(), media_type=media_type)
    raise HTTPException(status_code=404, detail="File not found")

