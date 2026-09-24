"""OpenStreetMap Infrastructure Ingestion & Dependency Graph Builder.

Extracts substations, hospitals, cyclone shelters, highways, bridges, and
telecom towers from OpenStreetMap data within the Area of Interest (AOI),
inferring operational dependencies and tagging assumptions.
"""

import math
from typing import Any, Dict, List, Optional, Tuple
from src.contracts import Edge, EdgeRelation, Facility, FacilityType


def haversine_distance_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Calculate geographic distance between coordinates in kilometers."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class OSMIngest:
    """Extracts, standardizes, and establishes infrastructure graphs from OSM datasets."""

    @staticmethod
    def extract_facilities(raw_osm_elements: Optional[List[Dict[str, Any]]] = None) -> List[Facility]:
        """Convert raw OSM nodes and ways into standardized Facility contracts."""
        if not raw_osm_elements:
            # Baseline pilot region infrastructure for Bengal Delta / Sundarbans
            raw_osm_elements = [
                {
                    "id": "osm:substation:kakdwip",
                    "type": FacilityType.SUBSTATION,
                    "name": "132/33kV Kakdwip Grid Substation",
                    "geometry": {"type": "Point", "coordinates": [88.185, 21.875]},
                    "elevation_m": 1.8,
                    "attributes": {"voltage_kv": 132, "transformers": 2, "criticality": "high"},
                    "assumption_fields": ["transformer_elevation_m"]
                },
                {
                    "id": "osm:substation:sagar",
                    "type": FacilityType.SUBSTATION,
                    "name": "33/11kV Sagar Island Substation",
                    "geometry": {"type": "Point", "coordinates": [88.080, 21.650]},
                    "elevation_m": 1.2,
                    "attributes": {"voltage_kv": 33, "transformers": 1, "criticality": "critical"},
                    "assumption_fields": ["flood_threshold_m"]
                },
                {
                    "id": "osm:hospital:kakdwip",
                    "type": FacilityType.HOSPITAL,
                    "name": "Kakdwip Sub-Divisional Hospital",
                    "geometry": {"type": "Point", "coordinates": [88.190, 21.870]},
                    "elevation_m": 2.1,
                    "attributes": {"bed_capacity": 250, "backup_power_hours": 8, "icu_units": 12},
                    "assumption_fields": ["backup_power_hours"]
                },
                {
                    "id": "osm:hospital:sagar",
                    "type": FacilityType.HOSPITAL,
                    "name": "Sagar Rural Hospital",
                    "geometry": {"type": "Point", "coordinates": [88.085, 21.660]},
                    "elevation_m": 1.9,
                    "attributes": {"bed_capacity": 100, "backup_power_hours": 6, "maternity_wing": True},
                    "assumption_fields": ["backup_power_hours"]
                },
                {
                    "id": "osm:shelter:sagar-01",
                    "type": FacilityType.SHELTER,
                    "name": "Sagar Central Multi-Purpose Cyclone Shelter",
                    "geometry": {"type": "Point", "coordinates": [88.075, 21.645]},
                    "elevation_m": 3.4,
                    "attributes": {"capacity": 1500, "water_storage_liters": 10000, "plinth_height_m": 1.2},
                    "assumption_fields": []
                },
                {
                    "id": "osm:shelter:namkhana-02",
                    "type": FacilityType.SHELTER,
                    "name": "Namkhana High School Cyclone Shelter",
                    "geometry": {"type": "Point", "coordinates": [88.230, 21.765]},
                    "elevation_m": 2.8,
                    "attributes": {"capacity": 950, "water_storage_liters": 6000, "plinth_height_m": 0.9},
                    "assumption_fields": []
                },
                {
                    "id": "osm:shelter:kakdwip-03",
                    "type": FacilityType.SHELTER,
                    "name": "Kakdwip Municipal Relief Centre",
                    "geometry": {"type": "Point", "coordinates": [88.195, 21.880]},
                    "elevation_m": 3.1,
                    "attributes": {"capacity": 1100, "water_storage_liters": 8000, "plinth_height_m": 1.0},
                    "assumption_fields": []
                },
                {
                    "id": "osm:road:nh12-segment",
                    "type": FacilityType.ROAD_SEGMENT,
                    "name": "NH-12 Coastal Highway Causeway (Kakdwip - Namkhana)",
                    "geometry": {"type": "LineString", "coordinates": [[88.185, 21.870], [88.210, 21.820], [88.230, 21.770]]},
                    "elevation_m": 1.4,
                    "attributes": {"lanes": 2, "surface": "asphalt", "clearance_m": 0.3},
                    "assumption_fields": ["light_vehicle_cutoff_m"]
                },
                {
                    "id": "osm:bridge:hatania",
                    "type": FacilityType.BRIDGE,
                    "name": "Hatania-Doania Estuary Bridge",
                    "geometry": {"type": "Point", "coordinates": [88.240, 21.770]},
                    "elevation_m": 4.8,
                    "attributes": {"structure": "concrete_girder", "max_tonnage": 40},
                    "assumption_fields": ["approach_road_vulnerability"]
                },
                {
                    "id": "osm:telecom:sagar-tower",
                    "type": FacilityType.TELECOM_TOWER,
                    "name": "Sagar Cellular Base Station Tower",
                    "geometry": {"type": "Point", "coordinates": [88.082, 21.655]},
                    "elevation_m": 1.5,
                    "attributes": {"battery_backup_hours": 4, "carriers": ["BSNL", "Airtel", "Jio"]},
                    "assumption_fields": ["battery_backup_hours"]
                }
            ]

        facilities = []
        for elem in raw_osm_elements:
            facilities.append(Facility.model_validate(elem))
        return facilities

    @staticmethod
    def infer_dependency_edges(facilities: List[Facility]) -> List[Edge]:
        """Infer electrical, logistical, and access links based on topology and spatial proximity."""
        edges = []
        substations = [f for f in facilities if f.type == FacilityType.SUBSTATION]
        hospitals = [f for f in facilities if f.type == FacilityType.HOSPITAL]
        towers = [f for f in facilities if f.type == FacilityType.TELECOM_TOWER]
        roads = [f for f in facilities if f.type == FacilityType.ROAD_SEGMENT]
        bridges = [f for f in facilities if f.type == FacilityType.BRIDGE]
        shelters = [f for f in facilities if f.type == FacilityType.SHELTER]

        # 1. Connect hospitals to nearest substation (Electrical Dependency)
        for h in hospitals:
            h_lon, h_lat = h.geometry["coordinates"]
            best_sub = None
            min_dist = float("inf")
            for s in substations:
                s_lon, s_lat = s.geometry["coordinates"]
                dist = haversine_distance_km(h_lon, h_lat, s_lon, s_lat)
                if dist < min_dist:
                    min_dist = dist
                    best_sub = s
            if best_sub:
                edges.append(Edge(
                    from_node=best_sub.id,
                    to_node=h.id,
                    relation=EdgeRelation.POWERS,
                    assumption=True
                ))

        # 2. Connect telecom towers to nearest substation
        for t in towers:
            t_lon, t_lat = t.geometry["coordinates"]
            best_sub = None
            min_dist = float("inf")
            for s in substations:
                s_lon, s_lat = s.geometry["coordinates"]
                dist = haversine_distance_km(t_lon, t_lat, s_lon, s_lat)
                if dist < min_dist:
                    min_dist = dist
                    best_sub = s
            if best_sub:
                edges.append(Edge(
                    from_node=best_sub.id,
                    to_node=t.id,
                    relation=EdgeRelation.POWERS,
                    assumption=True
                ))

        # 3. Connect hospitals and shelters to nearest road access
        for f in hospitals + shelters:
            f_lon, f_lat = f.geometry["coordinates"]
            for r in roads:
                # Approximate distance to road midpoint
                mid_lon, mid_lat = r.geometry["coordinates"][1]
                if haversine_distance_km(f_lon, f_lat, mid_lon, mid_lat) < 25.0:
                    edges.append(Edge(
                        from_node=r.id,
                        to_node=f.id,
                        relation=EdgeRelation.ACCESSES,
                        assumption=True
                    ))
                    break

        # 4. Bridge connectivity to neighboring shelters
        for b in bridges:
            b_lon, b_lat = b.geometry["coordinates"]
            for s in shelters:
                s_lon, s_lat = s.geometry["coordinates"]
                if haversine_distance_km(b_lon, b_lat, s_lon, s_lat) < 10.0:
                    edges.append(Edge(
                        from_node=b.id,
                        to_node=s.id,
                        relation=EdgeRelation.ACCESSES,
                        assumption=True
                    ))

        return edges
