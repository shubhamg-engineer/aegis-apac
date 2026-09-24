"""Contract Tests: Validates Golden Scenario data against frozen Pydantic contracts."""

import json
from pathlib import Path
import pytest
from src.contracts import (
    Facility,
    Edge,
    RiskResult,
    Action,
    Advisory,
    Scenario,
    ParametricResult,
)

GOLDEN_DIR = Path(__file__).parent.parent / "data" / "golden" / "amphan-2020"


def test_golden_scenario_valid():
    data = json.loads((GOLDEN_DIR / "scenario.json").read_text(encoding="utf-8"))
    scenario = Scenario.model_validate(data)
    assert scenario.id == "amphan-2020-t-72h"
    assert scenario.golden is True
    assert scenario.ensemble_members == 40


def test_golden_facilities_valid():
    data = json.loads((GOLDEN_DIR / "facilities.json").read_text(encoding="utf-8"))
    assert len(data) >= 5
    for item in data:
        facility = Facility.model_validate(item)
        assert facility.id.startswith("osm:")
        assert facility.elevation_m > 0
        assert facility.geometry["type"] in ["Point", "LineString"]


def test_golden_edges_valid():
    data = json.loads((GOLDEN_DIR / "edges.json").read_text(encoding="utf-8"))
    assert len(data) >= 4
    for item in data:
        edge = Edge.model_validate(item)
        assert edge.from_node != edge.to_node
        assert edge.assumption is True


def test_golden_risks_valid():
    data = json.loads((GOLDEN_DIR / "risks.json").read_text(encoding="utf-8"))
    assert len(data) >= 4
    for item in data:
        risk = RiskResult.model_validate(item)
        assert 0.0 <= risk.failure_probability <= 1.0
        assert risk.hours_of_warning > 0
        assert len(risk.cause_chain) >= 1


def test_golden_actions_valid():
    data = json.loads((GOLDEN_DIR / "actions.json").read_text(encoding="utf-8"))
    assert len(data) >= 3
    for item in data:
        action = Action.model_validate(item)
        assert action.district == "South 24 Parganas"
        assert len(action.supporting_risk_ids) >= 1
        assert 0.0 <= action.confidence <= 1.0


def test_golden_advisories_valid():
    data = json.loads((GOLDEN_DIR / "advisories.json").read_text(encoding="utf-8"))
    assert len(data) >= 3
    roles = set()
    languages = set()
    for item in data:
        adv = Advisory.model_validate(item)
        assert adv.validation.passed is True
        assert adv.validation.checked_values > 0
        roles.add(adv.role.value)
        languages.add(adv.language)
    
    assert "collector" in roles
    assert "en" in languages
    assert "bn" in languages


def test_golden_parametric_valid():
    data = json.loads((GOLDEN_DIR / "parametric.json").read_text(encoding="utf-8"))
    assert len(data) >= 1
    for item in data:
        param = ParametricResult.model_validate(item)
        assert 0.0 <= param.trigger_probability <= 1.0
        assert param.payout_amount_usd >= 0
        assert len(param.basis_risk) > 0
