"""Tests for Google Earth Engine (GEE) Ingestion & Offline Fallback."""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.ingest.gee import EarthEngineIngest


@pytest.fixture
def client():
    return TestClient(app)


def test_gee_connection_diagnostics():
    """Verify EarthEngineIngest diagnostics report proper catalog datasets and fallback mode."""
    ingest = EarthEngineIngest()
    status = ingest.check_connection()
    assert "ee_installed" in status
    assert "initialized" in status
    assert "mode" in status
    assert "catalog_datasets" in status
    assert status["catalog_datasets"]["dem"] == "COPERNICUS/DEM/GLO30_2024_1"
    assert status["catalog_datasets"]["rainfall"] == "NASA/GPM_L3/IMERG_V07"
    assert status["catalog_datasets"]["sentinel1"] == "COPERNICUS/S1_GRD"


def test_gee_copernicus_dem_extraction():
    """Verify DEM extraction returns compliant elevation grids and sea masks."""
    ingest = EarthEngineIngest()
    dem = ingest.extract_copernicus_dem(
        min_lon=87.8, min_lat=21.5, max_lon=88.5, max_lat=22.2, grid_shape=(30, 25)
    )
    assert "elevation_m" in dem
    assert "sea_mask" in dem
    assert "flow_accumulation" in dem
    assert dem["elevation_m"].shape == (30, 25)
    assert dem["sea_mask"].shape == (30, 25)


def test_gee_gpm_rainfall_extraction():
    """Verify GPM IMERG extraction returns valid accumulation grids across all timesteps."""
    ingest = EarthEngineIngest()
    dem = ingest.extract_copernicus_dem(grid_shape=(20, 20))
    rainfall = ingest.extract_gpm_rainfall(
        lons=dem["lons"],
        lats=dem["lats"],
        storm_name="amphan_2020",
    )
    assert set(rainfall.keys()) == {-24, -12, -6, 0, 6}
    for t, grid in rainfall.items():
        assert grid.shape == (20, 20)
        assert grid.min() >= 0.0


def test_gee_sentinel1_flood_extent():
    """Verify Sentinel-1 SAR backscatter change detection yields valid GeoJSON flood polygons."""
    ingest = EarthEngineIngest()
    s1_geojson = ingest.extract_sentinel1_flood_extent(storm_name="amphan_2020")
    assert s1_geojson["type"] == "FeatureCollection"
    assert len(s1_geojson["features"]) > 0
    assert "metadata" in s1_geojson
    assert s1_geojson["metadata"]["satellite_mission"] == "Copernicus Sentinel-1 SAR"
    assert s1_geojson["metadata"]["dataset_id"] == "COPERNICUS/S1_GRD"

    for feat in s1_geojson["features"]:
        assert feat["geometry"]["type"] == "Polygon"
        assert "backscatter_drop_db" in feat["properties"]


def test_gee_service_account_auto_detection(tmp_path):
    """Verify service account JSON keys can be passed explicitly or auto-detected."""
    fake_key_file = tmp_path / "mock-gee-key.json"
    fake_key_data = {
        "type": "service_account",
        "project_id": "test-gee-project-123",
        "client_email": "bot@test-gee-project-123.iam.gserviceaccount.com",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMOCK\n-----END PRIVATE KEY-----\n",
    }
    fake_key_file.write_text(json.dumps(fake_key_data), encoding="utf-8")

    ingest = EarthEngineIngest(service_account_json=str(fake_key_file))
    assert ingest.service_account_json == str(fake_key_file)
    assert ingest.service_account_email == "bot@test-gee-project-123.iam.gserviceaccount.com"
    assert ingest.project_id == "test-gee-project-123"


def test_api_gee_endpoints(client):
    """Verify /health and /api/v1/gee/status endpoints report GEE status."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "earth_engine" in data
    assert "components" in data
    assert "earth_engine" in data["components"]

    status_resp = client.get("/api/v1/gee/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert "catalog_datasets" in status_data
    assert "mode" in status_data
