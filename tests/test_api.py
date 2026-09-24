"""API Integration Tests: Validates all FastAPI endpoints and operator workflows."""

import os
from fastapi.testclient import TestClient
import pytest
from src.api.main import ADMIN_TOKEN, app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["demo_mode"] is True
    assert data["region"] == "bengal_delta"


def test_scenarios_endpoints():
    response = client.get("/scenarios")
    assert response.status_code == 200
    scenarios = response.json()
    assert len(scenarios) >= 1
    sc_id = scenarios[0]["id"]
    
    detail_res = client.get(f"/scenarios/{sc_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["name"].startswith("Cyclone Amphan")


def test_hazard_and_pathways_endpoints():
    response = client.get("/scenarios/amphan-2020-t-72h/hazard?t=0&threshold=0.3")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) >= 1
    
    pathways_res = client.get("/scenarios/amphan-2020-t-72h/pathways")
    assert pathways_res.status_code == 200
    p_data = pathways_res.json()
    assert p_data["type"] == "FeatureCollection"
    assert len(p_data["features"]) >= 1


def test_facilities_and_cascade_endpoints():
    response = client.get("/scenarios/amphan-2020-t-72h/facilities")
    assert response.status_code == 200
    facilities = response.json()
    assert len(facilities) >= 5
    
    # Test risk
    risk_res = client.get("/facilities/osm:substation:sagar/risk")
    assert risk_res.status_code == 200
    risk_data = risk_res.json()
    assert risk_data["failure_probability"] > 0.8
    assert risk_data["hours_of_warning"] == 66.0
    
    # Test cascade graph
    cascade_res = client.get("/facilities/osm:hospital:sagar/cascade")
    assert cascade_res.status_code == 200
    casc_data = cascade_res.json()
    assert casc_data["target_facility_id"] == "osm:hospital:sagar"
    assert len(casc_data["edges"]) >= 1
    assert len(casc_data["cause_chain"]) >= 2


def test_actions_and_parametric_endpoints():
    actions_res = client.get("/scenarios/amphan-2020-t-72h/actions")
    assert actions_res.status_code == 200
    actions = actions_res.json()
    assert len(actions) >= 3
    
    param_res = client.get("/scenarios/amphan-2020-t-72h/parametric")
    assert param_res.status_code == 200
    params = param_res.json()
    assert len(params) >= 1
    assert params[0]["trigger_probability"] >= 0.75
    assert params[0]["payout_triggered"] is True


def test_advisory_approval_workflow_and_cap_export():
    # 1. Fetch advisories
    adv_res = client.get("/advisories?scenario_id=amphan-2020-t-72h")
    assert adv_res.status_code == 200
    advisories = adv_res.json()
    target_adv = advisories[0]
    adv_id = target_adv["id"]
    
    # 2. Attempt approval without authorization token -> 401
    unauth_res = client.post(f"/advisories/{adv_id}/approve")
    assert unauth_res.status_code == 401
    
    # 3. Attempt approval with invalid token -> 401
    bad_token_res = client.post(
        f"/advisories/{adv_id}/approve",
        headers={"Authorization": "Bearer wrong_token"}
    )
    assert bad_token_res.status_code == 401
    
    # 4. Approve with valid operator token -> 200
    approved_res = client.post(
        f"/advisories/{adv_id}/approve?operator_name=DistrictCollector_South24Parganas",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
    )
    assert approved_res.status_code == 200
    approved_data = approved_res.json()
    assert approved_data["status"] == "approved"
    assert approved_data["history"][-1]["actor"] == "DistrictCollector_South24Parganas"
    
    # 5. Export CAP 1.2 XML
    cap_res = client.get(f"/advisories/{adv_id}/cap")
    assert cap_res.status_code == 200
    assert "application/xml" in cap_res.headers["content-type"]
    xml_content = cap_res.text
    assert "<alert" in xml_content
    assert f"AEGIS-APAC-{adv_id}" in xml_content
    assert "<status>Actual</status>" in xml_content


def test_backtest_metrics_endpoint():
    response = client.get("/backtest/amphan-2020/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "flood_extent_evaluation" in data
    assert data["flood_extent_evaluation"]["iou"] > 0.6
    assert len(data["baseline_comparison"]) == 3
