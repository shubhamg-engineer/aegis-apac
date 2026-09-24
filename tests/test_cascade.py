"""Unit tests for Phase 5 Infrastructure Cascade Engine.

Verifies:
1. Single direct failure cascades correctly to downstream dependents.
2. Backup-power duration delays hospital failure until generator fuel runs out.
3. Redundant power feeders prevent downstream outage.
4. Road access cutoff isolates shelters/hospitals.
5. Ensemble cascade produces ranked RiskResult list with cause chains.
"""

from datetime import datetime
import pytest

from src.contracts import Edge, EdgeRelation, Facility, FacilityType, RiskResult
from src.graph.cascade import CascadeEngine


@pytest.fixture
def toy_infrastructure_network():
    """Create a toy graph with 1 substation, 1 hospital, 1 road, and 1 shelter."""
    substation = Facility(
        id="sub_main",
        type=FacilityType.SUBSTATION,
        name="Main Coastal Substation",
        geometry={"type": "Point", "coordinates": [88.1, 21.6]},
        elevation_m=0.8,
        attributes={"voltage_kv": 132},
    )
    hospital = Facility(
        id="hosp_district",
        type=FacilityType.HOSPITAL,
        name="District General Hospital",
        geometry={"type": "Point", "coordinates": [88.2, 21.8]},
        elevation_m=2.5,
        attributes={"beds": 150, "backup_power_hours": 8.0},
    )
    road = Facility(
        id="road_access",
        type=FacilityType.ROAD_SEGMENT,
        name="State Highway 1 Access Road",
        geometry={"type": "LineString", "coordinates": [[88.1, 21.7], [88.2, 21.8]]},
        elevation_m=0.5,
        attributes={"lanes": 2},
    )
    shelter = Facility(
        id="shelter_cyclone",
        type=FacilityType.SHELTER,
        name="Cyclone Multi-Purpose Shelter",
        geometry={"type": "Point", "coordinates": [88.2, 21.75]},
        elevation_m=1.2,
        attributes={"capacity": 1000},
    )

    edges = [
        Edge(from_node="sub_main", to_node="hosp_district", relation=EdgeRelation.POWERS, assumption=True),
        Edge(from_node="road_access", to_node="hosp_district", relation=EdgeRelation.ACCESSES, assumption=True),
        Edge(from_node="road_access", to_node="shelter_cyclone", relation=EdgeRelation.ACCESSES, assumption=True),
    ]

    return {
        "facilities": [substation, hospital, road, shelter],
        "edges": edges,
    }


def test_backup_power_delays_hospital_failure(toy_infrastructure_network):
    """Substation fails at T-12h; hospital has 8h backup, so it must not fail at T-6h, only at T-0h."""
    engine = CascadeEngine()
    G = engine.build_graph(
        toy_infrastructure_network["facilities"],
        toy_infrastructure_network["edges"]
    )

    # Substation flooded at T-12h (depth 0.8m >= 0.4m threshold)
    # Hospital elevation is high (depth 0.0m), road is dry (depth 0.0m)
    timesteps = [-24, -12, -6, 0]
    depths = {
        -24: {"sub_main": 0.0, "hosp_district": 0.0, "road_access": 0.0, "shelter_cyclone": 0.0},
        -12: {"sub_main": 0.8, "hosp_district": 0.0, "road_access": 0.0, "shelter_cyclone": 0.0},
        -6:  {"sub_main": 1.0, "hosp_district": 0.0, "road_access": 0.0, "shelter_cyclone": 0.0},
        0:   {"sub_main": 1.2, "hosp_district": 0.0, "road_access": 0.0, "shelter_cyclone": 0.0},
    }

    # Test at T-6h (6h outage < 8h backup): hospital should still be operational
    state_at_minus_6 = engine.simulate_member(G, [-24, -12, -6], depths)
    assert state_at_minus_6["sub_main"]["failed"] is True
    assert state_at_minus_6["hosp_district"]["failed"] is False, "Hospital failed before backup generator exhausted!"

    # Test at T-0h (12h outage >= 8h backup): hospital must fail with power outage cause
    state_at_zero = engine.simulate_member(G, timesteps, depths)
    assert state_at_zero["hosp_district"]["failed"] is True
    assert "generator/battery exhausted" in state_at_zero["hosp_district"]["cause"]
    assert len(state_at_zero["hosp_district"]["chain"]) >= 2  # Substation cause + hospital cause


def test_redundant_power_feeders_prevent_failure():
    """If Substation 1 fails but Substation 2 is dry and also feeds the hospital, hospital does not fail."""
    engine = CascadeEngine()
    sub1 = Facility(id="sub1", type=FacilityType.SUBSTATION, name="Sub 1", geometry={"type": "Point", "coordinates": [0, 0]}, elevation_m=0.5)
    sub2 = Facility(id="sub2", type=FacilityType.SUBSTATION, name="Sub 2 (Backup)", geometry={"type": "Point", "coordinates": [0, 0]}, elevation_m=2.0)
    hosp = Facility(id="hosp", type=FacilityType.HOSPITAL, name="Redundant Hosp", geometry={"type": "Point", "coordinates": [0, 0]}, elevation_m=3.0, attributes={"backup_power_hours": 4.0})

    edges = [
        Edge(from_node="sub1", to_node="hosp", relation=EdgeRelation.POWERS, assumption=True),
        Edge(from_node="sub2", to_node="hosp", relation=EdgeRelation.POWERS, assumption=True),
    ]

    G = engine.build_graph([sub1, sub2, hosp], edges)

    # Sub 1 flooded, Sub 2 dry
    depths = {
        -12: {"sub1": 0.9, "sub2": 0.0, "hosp": 0.0},
        0:   {"sub1": 1.2, "sub2": 0.0, "hosp": 0.0},
    }

    state = engine.simulate_member(G, [-12, 0], depths)
    assert state["sub1"]["failed"] is True
    assert state["sub2"]["failed"] is False
    assert state["hosp"]["failed"] is False, "Hospital failed despite redundant operational substation!"


def test_road_access_cutoff_isolates_shelter(toy_infrastructure_network):
    """When the only access road to a shelter is submerged, shelter is marked failed/unusable."""
    engine = CascadeEngine()
    G = engine.build_graph(
        toy_infrastructure_network["facilities"],
        toy_infrastructure_network["edges"]
    )

    # Road flooded at T-6h (depth 0.5m >= 0.3m threshold); shelter plinth is dry
    depths = {
        -12: {"sub_main": 0.0, "hosp_district": 0.0, "road_access": 0.0, "shelter_cyclone": 0.0},
        -6:  {"sub_main": 0.0, "hosp_district": 0.0, "road_access": 0.5, "shelter_cyclone": 0.0},
    }

    state = engine.simulate_member(G, [-12, -6], depths)
    assert state["road_access"]["failed"] is True
    assert state["shelter_cyclone"]["failed"] is True
    assert "access routes impassable" in state["shelter_cyclone"]["cause"]


def test_ensemble_cascade_output_contracts(toy_infrastructure_network):
    """Run cascade across ensemble members and verify RiskResult contracts."""
    engine = CascadeEngine()

    # Create 10 mock ensemble members:
    # 8 members flood the substation, 5 members flood the road
    ensemble_depths = []
    for i in range(10):
        mem_depth = {
            -12: {
                "sub_main": 0.7 if i < 8 else 0.1,
                "road_access": 0.4 if i < 5 else 0.1,
                "hosp_district": 0.0,
                "shelter_cyclone": 0.0,
            },
            0: {
                "sub_main": 0.9 if i < 8 else 0.1,
                "road_access": 0.5 if i < 5 else 0.1,
                "hosp_district": 0.0,
                "shelter_cyclone": 0.0,
            }
        }
        ensemble_depths.append(mem_depth)

    results = engine.run_ensemble_cascade(
        facilities=toy_infrastructure_network["facilities"],
        edges=toy_infrastructure_network["edges"],
        ensemble_depths_by_member=ensemble_depths,
        timesteps_hours=[-12, 0],
        scenario_id="test-amphan",
        forecast_base_time=datetime(2020, 5, 17, 12, 0, 0),
    )

    assert len(results) == 4
    # All must be valid RiskResult instances
    for r in results:
        assert isinstance(r, RiskResult)
        assert 0.0 <= r.failure_probability <= 1.0
        assert r.hours_of_warning >= 0.0

    # Substation failed in 8/10 members -> 0.8
    sub_res = next(r for r in results if r.facility_id == "sub_main")
    assert sub_res.failure_probability == 0.8

    # Road failed in 5/10 members -> 0.5
    road_res = next(r for r in results if r.facility_id == "road_access")
    assert road_res.failure_probability == 0.5

    # Results are ranked by failure probability descending
    assert results[0].failure_probability >= results[-1].failure_probability
