"""Data Ingestion Test Suite: Verifies IBTrACS, OSM, Copernicus DEM, and GPM IMERG."""

import json
from pathlib import Path
import numpy as np
import pytest

from src.ingest.ibtracs import IBTrACSIngest
from src.ingest.osm import OSMIngest
from src.ingest.rainfall import RainfallIngest
from src.ingest.terrain import TerrainHydrology
from src.ingest.pipeline import run_pipeline

REPO_ROOT = Path(__file__).parent.parent
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "bengal_delta"


def test_ibtracs_track_ingestion():
    track = IBTrACSIngest.get_track("amphan_2020")
    assert len(track) >= 10
    
    # Check peak intensity reaches Super Cyclone
    max_wind = max(p.max_sustained_wind_kts for p in track)
    min_press = min(p.central_pressure_hpa for p in track)
    assert max_wind >= 135.0
    assert min_press <= 920.0
    
    # Check landfall point
    landfall = IBTrACSIngest.get_landfall_point("amphan_2020")
    assert landfall.timestamp == "2020-05-20T12:00:00Z"
    assert 21.0 <= landfall.latitude <= 22.0
    assert 88.0 <= landfall.longitude <= 89.0

    # Check pre-landfall filter (T-72h)
    filtered = IBTrACSIngest.get_track("amphan_2020", max_lead_time_utc="2020-05-17T12:00:00Z")
    assert len(filtered) == 3
    assert all(p.timestamp <= "2020-05-17T12:00:00Z" for p in filtered)

    # Check GeoJSON export
    geojson = IBTrACSIngest.export_geojson(track)
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == len(track) + 1


def test_osm_facility_and_edge_inference():
    facilities = OSMIngest.extract_facilities()
    assert len(facilities) >= 8
    
    types = {f.type.value for f in facilities}
    assert "substation" in types
    assert "hospital" in types
    assert "shelter" in types
    assert "road_segment" in types
    
    # Check inferred edges
    edges = OSMIngest.infer_dependency_edges(facilities)
    assert len(edges) >= 4
    for e in edges:
        assert e.assumption is True
        assert e.relation.value in ["powers", "accesses", "depends_on"]


def test_terrain_and_hydrology_processing():
    th = TerrainHydrology(min_lon=87.8, min_lat=21.5, max_lon=89.2, max_lat=22.8, grid_size=(60, 50))
    grid = th.generate_dem_grid()
    
    assert "elevation_m" in grid
    assert "sea_mask" in grid
    assert "flow_accumulation" in grid
    assert grid["elevation_m"].shape == (60, 50)
    assert grid["sea_mask"].dtype == np.uint8
    
    # Ocean points have elevation 0.0
    assert np.all(grid["elevation_m"][grid["sea_mask"] == 1] == 0.0)
    
    # Check drainage pathways
    pathways = th.extract_drainage_pathways()
    assert pathways["type"] == "FeatureCollection"
    assert len(pathways["features"]) >= 2


def test_rainfall_accumulation_grids():
    lons = np.linspace(87.8, 89.2, 50)
    lats = np.linspace(21.5, 22.8, 60)
    grids = RainfallIngest.generate_rainfall_grids(lons, lats, storm_landfall_lon=88.3, storm_landfall_lat=21.7)
    
    assert len(grids) == 5
    for t in [-24, -12, -6, 0, 6]:
        assert t in grids
        assert grids[t].shape == (60, 50)
        assert np.max(grids[t]) > 0.0
    
    # Cumulative rainfall monotonic check at core
    assert np.max(grids[0]) > np.max(grids[-12]) > np.max(grids[-24])


def test_pipeline_output_and_metadata():
    out_dir = run_pipeline(region_id="bengal_delta", storm_name="amphan_2020")
    assert out_dir.is_dir()

    expected_layers = [
        "dem_elevation.npz",
        "drainage_pathways.geojson",
        "facilities.json",
        "infrastructure_edges.json",
        "rainfall_accumulation.npz",
        "storm_track_amphan_2020.json",
    ]

    for layer in expected_layers:
        file_path = out_dir / layer
        meta_path = out_dir / f"{layer}.meta.json"
        
        assert file_path.is_file(), f"Layer file missing: {layer}"
        assert meta_path.is_file(), f"Metadata missing for: {layer}"
        
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        for req_field in ["layer_name", "source", "date_generated", "licence", "resolution", "crs", "attribution"]:
            assert req_field in meta, f"Metadata field '{req_field}' missing in {meta_path.name}"
            assert len(str(meta[req_field])) > 0
