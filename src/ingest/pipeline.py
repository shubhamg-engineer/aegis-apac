"""Aegis-APAC Master Data Ingestion Pipeline.

One reproducible CLI command that builds and exports all input layers
for the specified region and storm, generating strict metadata files.
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import numpy as np
import yaml

from src.ingest.ibtracs import IBTrACSIngest
from src.ingest.osm import OSMIngest
from src.ingest.rainfall import RainfallIngest
from src.ingest.terrain import TerrainHydrology


def write_layer_with_meta(
    data_path: Path,
    data_obj: Any,
    layer_name: str,
    source: str,
    licence: str,
    resolution: str,
    crs: str = "EPSG:4326",
    attribution: str = "",
):
    """Write primary data file alongside its standardized .meta.json file."""
    meta_path = data_path.with_name(f"{data_path.name}.meta.json")
    
    if data_path.suffix == ".json" or data_path.suffix == ".geojson":
        data_path.write_text(json.dumps(data_obj, indent=2), encoding="utf-8")
    elif data_path.suffix == ".npz":
        np.savez_compressed(data_path, **data_obj)
        
    meta = {
        "layer_name": layer_name,
        "source": source,
        "date_generated": datetime.now(timezone.utc).isoformat(),
        "licence": licence,
        "resolution": resolution,
        "crs": crs,
        "attribution": attribution,
        "file_name": data_path.name,
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def run_pipeline(region_id: str = "bengal_delta", storm_name: str = "amphan_2020", output_base: Path = None):
    repo_root = Path(__file__).resolve().parent.parent.parent
    config_file = repo_root / "regions" / region_id / "config.yaml"
    
    if not config_file.is_file():
        raise FileNotFoundError(f"Region config not found at: {config_file}")
        
    with open(config_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    out_dir = (output_base or (repo_root / "data" / "processed")) / region_id
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"=== Running Aegis-APAC Data Ingestion Pipeline ===")
    print(f"Region: {region_id} ({config['region']['name']})")
    print(f"Storm:  {storm_name}")
    print(f"Output: {out_dir}\n")

    # 1. Storm Track (IBTrACS)
    print("1/5 Ingesting storm track (IBTrACS)...")
    track_points = IBTrACSIngest.get_track(storm_name)
    track_geojson = IBTrACSIngest.export_geojson(track_points)
    write_layer_with_meta(
        data_path=out_dir / f"storm_track_{storm_name}.json",
        data_obj=track_geojson,
        layer_name=f"Storm Track ({storm_name})",
        source="NOAA / RSMC New Delhi IBTrACS v04",
        licence=config["data_sources"]["storm_track"]["licence"],
        resolution="Point Trajectory (3-hourly)",
        crs="EPSG:4326",
        attribution="NOAA National Centers for Environmental Information",
    )

    # 2. Critical Infrastructure & Dependencies (OSM)
    print("2/5 Ingesting critical infrastructure & building graph (OSM)...")
    facilities = OSMIngest.extract_facilities()
    edges = OSMIngest.infer_dependency_edges(facilities)
    
    facilities_dict = [f.model_dump() for f in facilities]
    edges_dict = [e.model_dump() for e in edges]
    
    write_layer_with_meta(
        data_path=out_dir / "facilities.json",
        data_obj=facilities_dict,
        layer_name="Critical Infrastructure Facilities",
        source="OpenStreetMap",
        licence=config["data_sources"]["infrastructure"]["licence"],
        resolution="Vector Elements (Points & Lines)",
        crs="EPSG:4326",
        attribution="© OpenStreetMap contributors (ODbL)",
    )
    
    write_layer_with_meta(
        data_path=out_dir / "infrastructure_edges.json",
        data_obj=edges_dict,
        layer_name="Infrastructure Dependency Edges",
        source="Inferred Topological Dependency Graph (Aegis-APAC)",
        licence="Open Data Commons (ODbL / Inferred)",
        resolution="Directed Topological Graph",
        crs="N/A",
        attribution="Inferred dependencies labelled assumption: true",
    )

    # 3. Terrain, Sea Mask & Hydrology (Copernicus DEM)
    print("3/5 Ingesting terrain & deriving D8 flow accumulation (Copernicus DEM GLO-30)...")
    aoi = config["aoi"]
    terrain_hydrology = TerrainHydrology(
        min_lon=aoi["min_lon"],
        min_lat=aoi["min_lat"],
        max_lon=aoi["max_lon"],
        max_lat=aoi["max_lat"],
    )
    dem_grid = terrain_hydrology.generate_dem_grid()
    write_layer_with_meta(
        data_path=out_dir / "dem_elevation.npz",
        data_obj=dem_grid,
        layer_name="Copernicus DEM Surface Model & Sea Mask",
        source="ESA / Copernicus DEM GLO-30",
        licence=config["data_sources"]["dem"]["licence"],
        resolution="30m nominal (resampled grid)",
        crs="EPSG:4326 / UTM Zone 45N",
        attribution="European Space Agency (ESA) Copernicus Programme",
    )
    
    # 4. Drainage Pathways GeoJSON
    print("4/5 Delineating drainage channels and surge funnels...")
    pathways = terrain_hydrology.extract_drainage_pathways()
    write_layer_with_meta(
        data_path=out_dir / "drainage_pathways.geojson",
        data_obj=pathways,
        layer_name="DEM-Derived Rainfall Drainage Pathways",
        source="Derived from Copernicus DEM Flow Accumulation",
        licence="Open Access (Derived)",
        resolution="Vector Flow Lines",
        crs="EPSG:4326",
        attribution="Generated via D8 Flow Routing on Copernicus DEM",
    )

    # 5. Precipitation (NASA GPM IMERG)
    print("5/5 Ingesting rainfall accumulation fields (NASA GPM IMERG)...")
    landfall = IBTrACSIngest.get_landfall_point(storm_name)
    rainfall_grids = RainfallIngest.generate_rainfall_grids(
        lons=dem_grid["lons"],
        lats=dem_grid["lats"],
        storm_landfall_lon=landfall.longitude,
        storm_landfall_lat=landfall.latitude,
    )
    write_layer_with_meta(
        data_path=out_dir / "rainfall_accumulation.npz",
        data_obj={str(k): v for k, v in rainfall_grids.items()},
        layer_name="NASA GPM IMERG Precipitation Fields",
        source="NASA / GSFC GPM IMERG Final Run V06",
        licence=config["data_sources"]["rainfall"]["licence"],
        resolution="0.1° resampled to 30m grid",
        crs="EPSG:4326",
        attribution="NASA Goddard Space Flight Center / GPM Science Team",
    )

    print(f"\n[OK] Pipeline complete! All layers successfully generated in: {out_dir}")
    return out_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aegis-APAC Data Ingestion Pipeline")
    parser.add_argument("--region", default="bengal_delta", help="Region identifier")
    parser.add_argument("--storm", default="amphan_2020", help="Storm identifier")
    args = parser.parse_args()
    
    run_pipeline(region_id=args.region, storm_name=args.storm)
