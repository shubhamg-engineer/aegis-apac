"""Unit tests for Phase 6 Decision Layer and Parametric Trigger Engine."""

from datetime import datetime
import numpy as np
import pytest

from src.contracts import Action, ActionType, Facility, FacilityType, ParametricResult, RiskResult
from src.decision.engine import DecisionEngine
from src.parametric.trigger import ParametricEngine


@pytest.fixture
def mock_decision_data():
    substation = Facility(
        id="sub_test",
        type=FacilityType.SUBSTATION,
        name="Substation Test",
        geometry={"type": "Point", "coordinates": [88.1, 21.6]},
        elevation_m=0.5,
    )
    hospital = Facility(
        id="hosp_test",
        type=FacilityType.HOSPITAL,
        name="Hospital Test",
        geometry={"type": "Point", "coordinates": [88.2, 21.8]},
        elevation_m=2.0,
    )
    road = Facility(
        id="road_test",
        type=FacilityType.ROAD_SEGMENT,
        name="Road Test",
        geometry={"type": "LineString", "coordinates": [[88.1, 21.6], [88.2, 21.8]]},
        elevation_m=0.4,
    )
    shelter = Facility(
        id="sh_test",
        type=FacilityType.SHELTER,
        name="Shelter Cyclone",
        geometry={"type": "Point", "coordinates": [88.15, 21.7]},
        elevation_m=1.5,
        attributes={"capacity": 500},
    )

    risks = [
        RiskResult(
            facility_id="sub_test",
            scenario_id="sc-test",
            failure_probability=0.85,
            earliest_failure_time="2020-05-20T08:00:00Z",
            hours_of_warning=16.0,
            cause_chain=[],
        ),
        RiskResult(
            facility_id="road_test",
            scenario_id="sc-test",
            failure_probability=0.70,
            earliest_failure_time="2020-05-20T06:00:00Z",
            hours_of_warning=14.0,
            cause_chain=[],
        ),
        RiskResult(
            facility_id="hosp_test",
            scenario_id="sc-test",
            failure_probability=0.55,
            earliest_failure_time="2020-05-20T14:00:00Z",
            hours_of_warning=22.0,
            cause_chain=[],
        ),
    ]

    return {
        "facilities": [substation, hospital, road, shelter],
        "risks": risks,
    }


def test_road_blockage_window_detection(mock_decision_data):
    engine = DecisionEngine(road_cutoff_depth_m=0.3)
    road = [f for f in mock_decision_data["facilities"] if f.type == FacilityType.ROAD_SEGMENT]

    depths = {
        -12: {"road_test": 0.1},
        -6:  {"road_test": 0.45},  # Blocked starting at -6h
        0:   {"road_test": 0.80},
        6:   {"road_test": 0.15},  # Cleared at 6h
    }

    windows = engine.compute_road_blockage_windows(road, depths, [-12, -6, 0, 6])
    assert "road_test" in windows
    assert windows["road_test"]["is_blocked"] is True
    assert windows["road_test"]["first_blocked_step_h"] == -6
    assert windows["road_test"]["last_blocked_step_h"] == 0


def test_shelter_allocation_capacity_constraints(mock_decision_data):
    engine = DecisionEngine()
    shelters = [f for f in mock_decision_data["facilities"] if f.type == FacilityType.SHELTER]
    risks_by_id = {r.facility_id: r for r in mock_decision_data["risks"]}

    # Population of 800 people trying to fit into shelter with capacity 500
    clusters = [
        {"name": "Coastal Village 1", "population": 800, "coordinates": [88.14, 21.69], "district": "Purba Medinipur"}
    ]

    allocations = engine.allocate_shelters(clusters, shelters, risks_by_id, {})
    assert len(allocations) == 1
    alloc = allocations[0]
    assert alloc["total_population"] == 800
    assert alloc["shelters"][0]["evacuees"] == 500
    assert alloc["unaccommodated"] == 300


def test_action_contracts_and_deadlines(mock_decision_data):
    engine = DecisionEngine()
    clusters = [
        {"name": "Ward A", "population": 400, "coordinates": [88.15, 21.7], "district": "Purba Medinipur"}
    ]

    actions = engine.generate_actions(
        facilities=mock_decision_data["facilities"],
        risks=mock_decision_data["risks"],
        population_clusters=clusters,
        forecast_base_time=datetime(2020, 5, 17, 12, 0, 0),
        district="Purba Medinipur",
    )

    assert len(actions) >= 4
    for act in actions:
        assert isinstance(act, Action)
        assert len(act.supporting_risk_ids) > 0
        assert act.confidence > 0.0
        assert act.deadline.endswith("Z")

    types = [a.type for a in actions]
    assert ActionType.DEENERGISE in types
    assert ActionType.CLOSE_ROAD in types
    assert ActionType.PROTECT_FACILITY in types
    assert ActionType.EVACUATE in types


def test_parametric_trigger_evaluation():
    p_engine = ParametricEngine()
    grid_shape = (20, 20)

    # 10 ensemble members:
    # 7 members exceed severe wind (45 m/s > 42 m/s) and depth (1.2m > 1.0m) over the district
    # 3 members do not
    ensemble_winds = []
    ensemble_depths = []
    for i in range(10):
        if i < 7:
            w = np.full(grid_shape, 46.0)
            d = np.full(grid_shape, 1.4)
        else:
            w = np.full(grid_shape, 25.0)
            d = np.full(grid_shape, 0.2)
        ensemble_winds.append(w)
        ensemble_depths.append(d)

    masks = {
        "Purba Medinipur": np.ones(grid_shape, dtype=np.uint8),
        "South 24 Parganas": np.ones(grid_shape, dtype=np.uint8),
        "Kendrapara": np.ones(grid_shape, dtype=np.uint8),
    }

    results = p_engine.evaluate_districts(ensemble_winds, ensemble_depths, masks)

    assert len(results) == 3
    for res in results:
        assert isinstance(res, ParametricResult)
        assert res.trigger_probability == 0.70
        assert res.payout_triggered is True  # 0.70 >= 0.60 threshold
        assert res.payout_amount_usd > 0.0
        assert "Basis Risk" in res.basis_risk
