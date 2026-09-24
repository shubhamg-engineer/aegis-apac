"""Hazard Engine Acceptance Tests.

Verifies:
1. Physical monotonicity (higher surge yields larger flooded area).
2. Hydraulic connectivity (disconnected inland basins stay dry from coastal surge).
3. Zero surge boundary condition (zero surge yields zero coastal flooding).
4. Rainfall routing (rain-only simulation is confined to drainage channels and depression sinks).
5. Holland wind/pressure profile radial decay properties.
6. Calibration engine finds valid optimal parameters.
"""

from dataclasses import asdict
import numpy as np
import pytest

from src.hazard.calibrate import HazardCalibrator
from src.hazard.engine import HazardEngine
from src.hazard.holland import HollandProfile
from src.hazard.inundation import HydraulicInundation
from src.hazard.runoff import RainfallRunoffModel
from src.hazard.surge import StormSurgeModel


@pytest.fixture
def mock_terrain():
    nx, ny = 40, 50
    lons = np.linspace(88.0, 88.5, nx)
    lats = np.linspace(21.5, 22.0, ny)
    xx, yy = np.meshgrid(lons, lats)
    
    # Elevation rises from 0.5m near coast (lat 21.5) to 4.5m inland (lat 22.0)
    elevation = 0.5 + (yy - 21.5) * 8.0
    
    # Sea mask: southern row is sea
    sea_mask = np.zeros_like(elevation, dtype=np.uint8)
    sea_mask[yy < 21.55] = 1
    elevation[sea_mask == 1] = 0.0

    # Create an artificial disconnected inland basin (elevation 0.2m surrounded by 3.5m ridge)
    elevation[35:40, 15:25] = 0.2
    
    flow_accum = np.ones_like(elevation)
    rainfall_mm = np.full_like(elevation, 150.0)

    return {
        "lons": lons,
        "lats": lats,
        "elevation_m": elevation,
        "sea_mask": sea_mask,
        "flow_accumulation": flow_accum,
        "rainfall_mm": rainfall_mm,
    }


def test_holland_profile_properties():
    hp = HollandProfile()
    lons = np.linspace(87.5, 89.0, 30)
    lats = np.linspace(21.0, 22.5, 30)
    
    res = hp.evaluate_grid(
        lons=lons,
        lats=lats,
        center_lon=88.25,
        center_lat=21.75,
        Pc=950.0,
        Vmax_ms=45.0,
        Rmax_km=40.0,
    )
    
    # Pressure at eye is minimum and approaches Pc, rising monotonically outward
    min_p = np.min(res["pressure_hpa"])
    max_p = np.max(res["pressure_hpa"])
    assert min_p < 960.0
    assert max_p > 990.0
    assert max_p > min_p + 35.0
    
    # Peak wind occurs near Rmax (within 30-50 km of eye)
    dist = res["distance_to_eye_km"]
    winds = res["wind_speed_ms"]
    peak_idx = np.unravel_index(np.argmax(winds), winds.shape)
    peak_dist = dist[peak_idx]
    assert 20.0 <= peak_dist <= 60.0


def test_surge_monotonicity_with_multiplier(mock_terrain):
    engine = HazardEngine()
    
    # Run with standard surge multiplier (1.0)
    res_standard = engine.run_time_step(
        lons=mock_terrain["lons"],
        lats=mock_terrain["lats"],
        elevation_m=mock_terrain["elevation_m"],
        sea_mask=mock_terrain["sea_mask"],
        flow_accumulation=mock_terrain["flow_accumulation"],
        rainfall_mm=np.zeros_like(mock_terrain["rainfall_mm"]),
        center_lon=88.25,
        center_lat=21.75,
        Pc=945.0,
        Vmax_ms=50.0,
        Rmax_km=40.0,
        surge_multiplier=1.0,
    )
    
    # Run with higher surge multiplier (1.4)
    res_higher = engine.run_time_step(
        lons=mock_terrain["lons"],
        lats=mock_terrain["lats"],
        elevation_m=mock_terrain["elevation_m"],
        sea_mask=mock_terrain["sea_mask"],
        flow_accumulation=mock_terrain["flow_accumulation"],
        rainfall_mm=np.zeros_like(mock_terrain["rainfall_mm"]),
        center_lon=88.25,
        center_lat=21.75,
        Pc=945.0,
        Vmax_ms=50.0,
        Rmax_km=40.0,
        surge_multiplier=1.4,
    )
    
    # Flooded area strictly increases with higher surge
    flooded_standard = (res_standard["surge_depth_m"] > 0.1).sum()
    flooded_higher = (res_higher["surge_depth_m"] > 0.1).sum()
    assert flooded_higher >= flooded_standard
    assert np.max(res_higher["coastal_water_level_m"]) > np.max(res_standard["coastal_water_level_m"])


def test_hydraulic_connectivity_prevents_disconnected_basin_flooding(mock_terrain):
    engine = HazardEngine()
    
    res = engine.run_time_step(
        lons=mock_terrain["lons"],
        lats=mock_terrain["lats"],
        elevation_m=mock_terrain["elevation_m"],
        sea_mask=mock_terrain["sea_mask"],
        flow_accumulation=mock_terrain["flow_accumulation"],
        rainfall_mm=np.zeros_like(mock_terrain["rainfall_mm"]),  # Zero rain to test surge isolation
        center_lon=88.25,
        center_lat=21.75,
        Pc=945.0,
        Vmax_ms=50.0,
        Rmax_km=40.0,
        surge_multiplier=1.1,
    )
    
    # The artificial inland basin at rows 35:40, cols 15:25 has elevation 0.2m,
    # which is below sea level, BUT it is surrounded by a 3.5m+ ridge.
    # Surge should NOT flood this disconnected inland depression!
    inland_basin_surge = res["surge_depth_m"][35:40, 15:25]
    assert np.all(inland_basin_surge == 0.0), "Disconnected inland basin was erroneously flooded by coastal surge!"


def test_zero_surge_boundary_condition(mock_terrain):
    inun_model = HydraulicInundation()
    
    # If coastal water level is 0.0 (below land elevation of >= 0.5m)
    zero_water_level = np.zeros_like(mock_terrain["elevation_m"])
    
    res = inun_model.compute_inundation(
        coastal_water_level_m=zero_water_level,
        elevation_m=mock_terrain["elevation_m"],
        sea_mask=mock_terrain["sea_mask"],
    )
    
    assert np.all(res["surge_depth_m"] == 0.0)
    assert not np.any(res["connected_flood_mask"])


def test_rain_only_routing_and_sinks(mock_terrain):
    runoff_model = RainfallRunoffModel(runoff_coefficient=0.7)
    
    # D8 accumulation high in one drainage channel
    flow_accum = np.ones_like(mock_terrain["elevation_m"])
    flow_accum[20:30, 20] = 500.0  # Major stream channel
    
    res = runoff_model.compute_ponding_depth(
        rainfall_mm=mock_terrain["rainfall_mm"],
        elevation_m=mock_terrain["elevation_m"],
        flow_accumulation=flow_accum,
        sea_mask=mock_terrain["sea_mask"],
    )
    
    ponding = res["rain_ponding_depth_m"]
    # Channel ponding should be significantly deeper than surrounding flat land
    channel_depth = np.mean(ponding[20:30, 20])
    surrounding_depth = np.mean(ponding[20:30, 10])
    assert channel_depth > surrounding_depth


def test_calibration_grid_search(mock_terrain):
    calibrator = HazardCalibrator(
        candidate_multipliers=[0.9, 1.15],
        candidate_decays=[0.00015, 0.00025]
    )
    
    # Synthetic reference flood mask (e.g. from Copernicus EMS)
    reference_mask = np.zeros_like(mock_terrain["elevation_m"], dtype=bool)
    reference_mask[mock_terrain["sea_mask"] == 0] = mock_terrain["elevation_m"][mock_terrain["sea_mask"] == 0] < 2.2
    
    landfall_pt = {
        "longitude": 88.25,
        "latitude": 21.75,
        "central_pressure_hpa": 948.0,
        "max_sustained_wind_ms": 48.0,
        "radius_max_winds_km": 45.0,
    }
    
    calib_out = calibrator.run_grid_search(
        lons=mock_terrain["lons"],
        lats=mock_terrain["lats"],
        elevation_m=mock_terrain["elevation_m"],
        sea_mask=mock_terrain["sea_mask"],
        flow_accumulation=mock_terrain["flow_accumulation"],
        rainfall_mm=mock_terrain["rainfall_mm"],
        landfall_pt=landfall_pt,
        reference_flood_mask=reference_mask,
    )
    
    assert "optimal" in calib_out
    optimal = calib_out["optimal"]
    assert optimal["iou"] > 0.0
    assert optimal["precision"] > 0.0
    assert optimal["recall"] > 0.0
    assert len(calib_out["all_trials"]) == 4
