"""Unit and property tests for Phase 4 Ensemble Hazard Generator."""

import numpy as np
import pytest

from src.hazard.ensemble import EnsembleHazardGenerator, IMD_ERROR_STATS


@pytest.fixture
def mock_aoi_grid():
    """Create a lightweight synthetic domain for testing ensemble operations."""
    lon = np.linspace(88.0, 89.0, 25)
    lat = np.linspace(21.5, 22.5, 25)
    lons, lats = np.meshgrid(lon, lat)

    # South is ocean (sea_mask=1), North is land sloping upward
    sea_mask = np.zeros_like(lats, dtype=np.uint8)
    sea_mask[lats < 21.75] = 1

    elevation_m = (lats - 21.75) * 5.0  # 0 to ~3.75m elevation
    elevation_m[sea_mask == 1] = 0.0

    flow_acc = np.ones_like(elevation_m)
    rainfall_mm = np.full_like(elevation_m, 120.0)

    return {
        "lons": lons,
        "lats": lats,
        "sea_mask": sea_mask,
        "elevation_m": elevation_m,
        "flow_accumulation": flow_acc,
        "rainfall_mm": rainfall_mm,
    }


def test_imd_error_scaling():
    """Verify that forecast perturbations scale inversely with lead time."""
    generator = EnsembleHazardGenerator(num_members=30, random_seed=42)

    err_72h = generator.get_lead_time_errors(72.0)
    err_48h = generator.get_lead_time_errors(48.0)
    err_24h = generator.get_lead_time_errors(24.0)

    assert err_72h["along_track_km"] >= err_48h["along_track_km"]
    assert err_48h["along_track_km"] >= err_24h["along_track_km"]

    assert err_72h["pc_hpa"] >= err_48h["pc_hpa"]
    assert err_48h["pc_hpa"] >= err_24h["pc_hpa"]


def test_member_parameters_generation():
    """Verify unperturbed member 0 and perturbed member bounds."""
    generator = EnsembleHazardGenerator(num_members=35, random_seed=123)
    members = generator.generate_member_parameters(
        center_lon=88.5,
        center_lat=21.8,
        motion_bearing_deg=30.0,
        base_pc_hpa=950.0,
        base_vmax_ms=45.0,
        base_rmw_km=35.0,
        lead_time_hours=72.0,
    )

    assert len(members) == 35

    # Member 0 must be identical to unperturbed input
    m0 = members[0]
    assert m0["member_id"] == 0
    assert m0["center_lon"] == 88.5
    assert m0["center_lat"] == 21.8
    assert m0["Pc"] == 950.0

    # Perturbed members must have varied tracks and pressures within realistic bounds
    pcs = [m["Pc"] for m in members]
    assert min(pcs) < 950.0 or max(pcs) > 950.0
    for m in members:
        assert 890.0 <= m["Pc"] <= 1010.0
        assert 15.0 <= m["Rmax_km"] <= 80.0


def test_ensemble_probability_bounds_and_monotonicity(mock_aoi_grid):
    """Ensemble probabilities must be bounded [0, 1] and strictly monotonic P(>1.0m) <= P(>0.3m)."""
    generator = EnsembleHazardGenerator(num_members=15, random_seed=42)
    members_params = generator.generate_member_parameters(
        center_lon=88.5,
        center_lat=21.6,
        motion_bearing_deg=35.0,
        base_pc_hpa=935.0,
        base_vmax_ms=50.0,
        base_rmw_km=30.0,
        lead_time_hours=48.0,
    )

    res = generator.run_ensemble_timestep(
        lons=mock_aoi_grid["lons"],
        lats=mock_aoi_grid["lats"],
        elevation_m=mock_aoi_grid["elevation_m"],
        sea_mask=mock_aoi_grid["sea_mask"],
        flow_accumulation=mock_aoi_grid["flow_accumulation"],
        rainfall_mm=mock_aoi_grid["rainfall_mm"],
        members_params=members_params,
    )

    p03 = res["prob_depth_03m"]
    p10 = res["prob_depth_10m"]

    # Bounds
    assert np.all(p03 >= 0.0) and np.all(p03 <= 1.0)
    assert np.all(p10 >= 0.0) and np.all(p10 <= 1.0)

    # Monotonicity
    assert np.all(p10 <= p03 + 1e-6), "Monotonicity violated: P(depth>1.0) > P(depth>0.3)"

    # Sea mask should be masked to zero
    assert np.all(p03[mock_aoi_grid["sea_mask"] == 1] == 0.0)
    assert np.all(p10[mock_aoi_grid["sea_mask"] == 1] == 0.0)

    # Runtime must be recorded
    assert res["runtime_sec"] > 0.0


def test_multi_timestep_ensemble_execution(mock_aoi_grid):
    """Multi-timestep ensemble tracks earliest exceedance step correctly."""
    generator = EnsembleHazardGenerator(num_members=10, random_seed=99)

    track = {
        -12: {"center_lon": 88.2, "center_lat": 21.4, "pc_hpa": 945.0, "vmax_ms": 48.0, "rmw_km": 30.0},
        0:   {"center_lon": 88.5, "center_lat": 21.8, "pc_hpa": 935.0, "vmax_ms": 52.0, "rmw_km": 30.0},
    }
    rainfall = {
        -12: np.full_like(mock_aoi_grid["elevation_m"], 50.0),
        0:   np.full_like(mock_aoi_grid["elevation_m"], 150.0),
    }

    res = generator.run_multi_timestep_ensemble(
        lons=mock_aoi_grid["lons"],
        lats=mock_aoi_grid["lats"],
        elevation_m=mock_aoi_grid["elevation_m"],
        sea_mask=mock_aoi_grid["sea_mask"],
        flow_accumulation=mock_aoi_grid["flow_accumulation"],
        timesteps_rainfall=rainfall,
        timesteps_track=track,
        lead_time_at_landfall=72.0,
    )

    assert res["total_runtime_sec"] > 0.0
    assert len(res["timesteps"]) == 2
    assert -12 in res["results_by_timestep"]
    assert 0 in res["results_by_timestep"]
    assert "earliest_exceedance_step" in res
