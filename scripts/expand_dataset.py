import json
from pathlib import Path

GOLDEN_DIR = Path("data/golden/amphan-2020")

# 1. Existing 10 facilities (keep exact IDs and data)
existing_facilities = json.loads((GOLDEN_DIR / "facilities.json").read_text(encoding="utf-8"))

# 2. Additional multi-district facilities
new_facilities = [
    # Kolkata Metropolitan Area
    {
        "id": "osm:hospital:sskm",
        "type": "hospital",
        "name": "SSKM Multi-Speciality Medical Hospital (Kolkata)",
        "geometry": {"type": "Point", "coordinates": [88.342, 22.539]},
        "elevation_m": 6.2,
        "attributes": {"bed_capacity": 1800, "backup_power_hours": 24, "icu_units": 65, "district": "Kolkata"},
        "assumption_fields": ["backup_power_hours"]
    },
    {
        "id": "osm:substation:cesc_central",
        "type": "substation",
        "name": "CESC Central 132kV Receiving Substation (Kolkata)",
        "geometry": {"type": "Point", "coordinates": [88.356, 22.568]},
        "elevation_m": 5.8,
        "attributes": {"voltage_kv": 132, "transformers": 4, "criticality": "critical", "district": "Kolkata"},
        "assumption_fields": ["flood_threshold_m"]
    },
    {
        "id": "osm:shelter:howrah_station",
        "type": "shelter",
        "name": "Howrah Emergency Transit Relief Center",
        "geometry": {"type": "Point", "coordinates": [88.343, 22.583]},
        "elevation_m": 6.0,
        "attributes": {"capacity": 3500, "water_storage_liters": 25000, "plinth_height_m": 1.5, "district": "Howrah"},
        "assumption_fields": []
    },
    {
        "id": "osm:telecom:kolkata_hub",
        "type": "telecom_tower",
        "name": "Kolkata State Emergency Telecom Gateway",
        "geometry": {"type": "Point", "coordinates": [88.351, 22.572]},
        "elevation_m": 5.5,
        "attributes": {"battery_backup_hours": 12, "carriers": ["BSNL", "Airtel", "Jio", "Vodafone"], "district": "Kolkata"},
        "assumption_fields": ["battery_backup_hours"]
    },

    # Purba Medinipur / Haldia Industrial Port Belt
    {
        "id": "osm:substation:haldia_grid",
        "type": "substation",
        "name": "Haldia Petrochemical 220kV Grid Substation",
        "geometry": {"type": "Point", "coordinates": [88.062, 22.025]},
        "elevation_m": 3.2,
        "attributes": {"voltage_kv": 220, "transformers": 3, "criticality": "critical", "district": "Purba Medinipur"},
        "assumption_fields": ["transformer_elevation_m"]
    },
    {
        "id": "osm:hospital:haldia_port",
        "type": "hospital",
        "name": "Haldia Port Trust Hospital",
        "geometry": {"type": "Point", "coordinates": [88.083, 22.031]},
        "elevation_m": 3.5,
        "attributes": {"bed_capacity": 150, "backup_power_hours": 10, "icu_units": 8, "district": "Purba Medinipur"},
        "assumption_fields": ["backup_power_hours"]
    },
    {
        "id": "osm:shelter:haldia_civic",
        "type": "shelter",
        "name": "Haldia Industrial Multi-Purpose Cyclone Shelter",
        "geometry": {"type": "Point", "coordinates": [88.075, 22.040]},
        "elevation_m": 4.0,
        "attributes": {"capacity": 2000, "water_storage_liters": 15000, "plinth_height_m": 1.2, "district": "Purba Medinipur"},
        "assumption_fields": []
    },
    {
        "id": "osm:bridge:haldi_river",
        "type": "bridge",
        "name": "Haldi River Rail-Road Causeway Bridge",
        "geometry": {"type": "Point", "coordinates": [88.021, 22.085]},
        "elevation_m": 5.1,
        "attributes": {"structure": "steel_truss", "max_tonnage": 60, "district": "Purba Medinipur"},
        "assumption_fields": ["approach_road_vulnerability"]
    },

    # Purba Medinipur / Digha & Mandarmani Coastal Belt
    {
        "id": "osm:shelter:digha_cyclone",
        "type": "shelter",
        "name": "Digha Coastal Multi-Purpose Cyclone Shelter",
        "geometry": {"type": "Point", "coordinates": [87.518, 21.628]},
        "elevation_m": 4.2,
        "attributes": {"capacity": 2200, "water_storage_liters": 18000, "plinth_height_m": 1.4, "district": "Purba Medinipur"},
        "assumption_fields": []
    },
    {
        "id": "osm:substation:digha_33kv",
        "type": "substation",
        "name": "Digha Coastal 33/11kV Substation",
        "geometry": {"type": "Point", "coordinates": [87.525, 21.632]},
        "elevation_m": 2.4,
        "attributes": {"voltage_kv": 33, "transformers": 2, "criticality": "high", "district": "Purba Medinipur"},
        "assumption_fields": ["flood_threshold_m"]
    },
    {
        "id": "osm:hospital:digha_state",
        "type": "hospital",
        "name": "Digha State General Hospital",
        "geometry": {"type": "Point", "coordinates": [87.535, 21.637]},
        "elevation_m": 3.1,
        "attributes": {"bed_capacity": 120, "backup_power_hours": 8, "icu_units": 6, "district": "Purba Medinipur"},
        "assumption_fields": ["backup_power_hours"]
    },
    {
        "id": "osm:telecom:digha_radar",
        "type": "telecom_tower",
        "name": "IMD Coastal Doppler Radar & Weather Station",
        "geometry": {"type": "Point", "coordinates": [87.512, 21.622]},
        "elevation_m": 5.8,
        "attributes": {"battery_backup_hours": 16, "carriers": ["IMD_Relay", "BSNL"], "district": "Purba Medinipur"},
        "assumption_fields": ["battery_backup_hours"]
    },

    # South 24 Parganas / Diamond Harbour & Canning Gateway
    {
        "id": "osm:hospital:diamond_harbour",
        "type": "hospital",
        "name": "Diamond Harbour Super-Speciality Hospital",
        "geometry": {"type": "Point", "coordinates": [88.192, 22.195]},
        "elevation_m": 3.8,
        "attributes": {"bed_capacity": 400, "backup_power_hours": 14, "icu_units": 20, "district": "South 24 Parganas"},
        "assumption_fields": ["backup_power_hours"]
    },
    {
        "id": "osm:substation:diamond_33kv",
        "type": "substation",
        "name": "Diamond Harbour 33kV Riverfront Substation",
        "geometry": {"type": "Point", "coordinates": [88.188, 22.198]},
        "elevation_m": 2.9,
        "attributes": {"voltage_kv": 33, "transformers": 2, "criticality": "high", "district": "South 24 Parganas"},
        "assumption_fields": ["flood_threshold_m"]
    },
    {
        "id": "osm:shelter:canning_relief",
        "type": "shelter",
        "name": "Canning Sundarbans Gateway Cyclone Shelter",
        "geometry": {"type": "Point", "coordinates": [88.665, 22.312]},
        "elevation_m": 2.5,
        "attributes": {"capacity": 1800, "water_storage_liters": 12000, "plinth_height_m": 1.1, "district": "South 24 Parganas"},
        "assumption_fields": []
    },
    {
        "id": "osm:substation:canning_33kv",
        "type": "substation",
        "name": "Canning 33/11kV Delta Feeder Substation",
        "geometry": {"type": "Point", "coordinates": [88.658, 22.318]},
        "elevation_m": 2.2,
        "attributes": {"voltage_kv": 33, "transformers": 2, "criticality": "high", "district": "South 24 Parganas"},
        "assumption_fields": ["transformer_elevation_m"]
    },

    # North 24 Parganas / Sundarbans Interior (Gosaba & Basirhat)
    {
        "id": "osm:shelter:gosaba_island",
        "type": "shelter",
        "name": "Gosaba Sundarbans Community Cyclone Shelter",
        "geometry": {"type": "Point", "coordinates": [88.805, 22.165]},
        "elevation_m": 2.1,
        "attributes": {"capacity": 1400, "water_storage_liters": 10000, "plinth_height_m": 1.3, "district": "South 24 Parganas"},
        "assumption_fields": []
    },
    {
        "id": "osm:substation:gosaba_solar",
        "type": "substation",
        "name": "Gosaba Island Solar Microgrid Substation",
        "geometry": {"type": "Point", "coordinates": [88.802, 22.162]},
        "elevation_m": 1.8,
        "attributes": {"voltage_kv": 11, "transformers": 1, "criticality": "critical", "district": "South 24 Parganas"},
        "assumption_fields": ["flood_threshold_m"]
    },
    {
        "id": "osm:hospital:basirhat_district",
        "type": "hospital",
        "name": "Basirhat District Hospital (North 24 Parganas)",
        "geometry": {"type": "Point", "coordinates": [88.895, 22.658]},
        "elevation_m": 4.1,
        "attributes": {"bed_capacity": 300, "backup_power_hours": 12, "icu_units": 15, "district": "North 24 Parganas"},
        "assumption_fields": ["backup_power_hours"]
    },
    {
        "id": "osm:shelter:hingalganj",
        "type": "shelter",
        "name": "Hingalganj Border Multi-Purpose Shelter",
        "geometry": {"type": "Point", "coordinates": [88.985, 22.472]},
        "elevation_m": 2.3,
        "attributes": {"capacity": 1200, "water_storage_liters": 9000, "plinth_height_m": 1.0, "district": "North 24 Parganas"},
        "assumption_fields": []
    },

    # Coastal South / Bakkhali & Frazerganj
    {
        "id": "osm:shelter:bakkhali_tourist",
        "type": "shelter",
        "name": "Bakkhali Coastal Multi-Purpose Shelter",
        "geometry": {"type": "Point", "coordinates": [88.258, 21.564]},
        "elevation_m": 3.2,
        "attributes": {"capacity": 1600, "water_storage_liters": 14000, "plinth_height_m": 1.2, "district": "South 24 Parganas"},
        "assumption_fields": []
    },
    {
        "id": "osm:substation:frazerganj_33kv",
        "type": "substation",
        "name": "Frazerganj Fishing Harbor 33/11kV Substation",
        "geometry": {"type": "Point", "coordinates": [88.252, 21.578]},
        "elevation_m": 1.9,
        "attributes": {"voltage_kv": 33, "transformers": 1, "criticality": "high", "district": "South 24 Parganas"},
        "assumption_fields": ["flood_threshold_m"]
    }
]

all_facilities = existing_facilities + new_facilities
(GOLDEN_DIR / "facilities.json").write_text(json.dumps(all_facilities, indent=2), encoding="utf-8")
print(f"Total facilities updated: {len(all_facilities)}")

# 3. Update risks.json
existing_risks = json.loads((GOLDEN_DIR / "risks.json").read_text(encoding="utf-8"))
existing_risk_ids = {r["facility_id"] for r in existing_risks}

new_risks = [
    # Kolkata
    {
        "facility_id": "osm:hospital:sskm",
        "scenario_id": "amphan-2020-t-72h",
        "failure_probability": 0.22,
        "earliest_failure_time": "2020-05-20T16:00:00Z",
        "hours_of_warning": 76.0,
        "cause_chain": [
            {"node": "osm:substation:cesc_central", "event": "voltage_sag_grid_surge", "probability": 0.35, "assumption": true},
            {"node": "osm:hospital:sskm", "event": "emergency_genset_active", "probability": 0.22, "assumption": false}
        ]
    },
    {
        "facility_id": "osm:substation:cesc_central",
        "scenario_id": "amphan-2020-t-72h",
        "failure_probability": 0.35,
        "earliest_failure_time": "2020-05-20T14:00:00Z",
        "hours_of_warning": 74.0,
        "cause_chain": [
            {"node": "osm:substation:cesc_central", "event": "urban_waterlogging_0.35m", "probability": 0.35, "assumption": false}
        ]
    },
    {
        "facility_id": "osm:shelter:howrah_station",
        "scenario_id": "amphan-2020-t-72h",
        "failure_probability": 0.18,
        "earliest_failure_time": "2020-05-20T18:00:00Z",
        "hours_of_warning": 78.0,
        "cause_chain": [
            {"node": "osm:shelter:howrah_station", "event": "concourse_access_road_submerged", "probability": 0.18, "assumption": true}
        ]
    },
    {
        "facility_id": "osm:telecom:kolkata_hub",
        "scenario_id": "amphan-2020-t-72h",
        "failure_probability": 0.28,
        "earliest_failure_time": "2020-05-20T15:00:00Z",
        "hours_of_warning": 75.0,
        "cause_chain": [
            {"node": "osm:substation:cesc_central", "event": "feeder_tripped_gale_gusts", "probability": 0.35, "assumption": true},
            {"node": "osm:telecom:kolkata_hub", "event": "diesel_backup_running", "probability": 0.28, "assumption": false}
        ]
    },

    # Haldia
    {
        "facility_id": "osm:substation:haldia_grid",
        "scenario_id": "amphan-2020-t-72h",
        "failure_probability": 0.74,
        "earliest_failure_time": "2020-05-20T08:00:00Z",
        "hours_of_warning": 68.0,
        "cause_chain": [
            {"node": "osm:substation:haldia_grid", "event": "storm_surge_overtopping_0.58m", "probability": 0.74, "assumption": false}
        ]
    },
    {
        "facility_id": "osm:hospital:haldia_port",
        "scenario_id": "amphan-2020-t-72h",
        "failure_probability": 0.68,
        "earliest_failure_time": "2020-05-20T12:00:00Z",
        "hours_of_warning": 72.0,
        "cause_chain": [
            {"node": "osm:substation:haldia_grid", "event": "storm_surge_overtopping_0.58m", "probability": 0.74, "assumption": false},
            {"node": "osm:hospital:haldia_port", "event": "generator_fuel_exhausted_after_10h", "probability": 0.68, "assumption": true}
        ]
    },
    {
        "facility_id": "osm:shelter:haldia_civic",
        "scenario_id": "amphan-2020-t-72h",
        "failure_probability": 0.25,
        "earliest_failure_time": "2020-05-20T13:00:00Z",
        "hours_of_warning": 73.0,
        "cause_chain": [
            {"node": "osm:shelter:haldia_civic", "event": "access_road_partially_cut", "probability": 0.25, "assumption": true}
        ]
    },
    {
        "facility_id": "osm:bridge:haldi_river",
        "scenario_id": "amphan-2020-t-72h",
        "failure_probability": 0.55,
        "earliest_failure_time": "2020-05-20T09:00:00Z",
        "hours_of_warning": 69.0,
        "cause_chain": [
            {"node": "osm:bridge:haldi_river", "event": "estuary_surge_wave_impact", "probability": 0.55, "assumption": false}
        ]
    },

    # Digha
    {
        "facility_id": "osm:substation:digha_33kv",
        "scenario_id": "amphan-2020-t-72h",
        "failure_probability": 0.84,
        "earliest_failure_time": "2020-05-20T05:30:00Z",
        "hours_of_warning": 65.5,
        "cause_chain": [
            {"node": "osm:substation:digha_33kv", "event": "direct_marine_surge_0.75m", "probability": 0.84, "assumption": false}
        ]
    },
    {
        "facility_id": "osm:hospital:digha_state",
        "scenario_id": "amphan-2020-t-72h",
        "failure_probability": 0.76,
        "earliest_failure_time": "2020-05-20T10:00:00Z",
        "hours_of_warning": 70.0,
        "cause_chain": [
            {"node": "osm:substation:digha_33kv", "event": "direct_marine_surge_0.75m", "probability": 0.84, "assumption": false},
            {"node": "osm:hospital:digha_state", "event": "inundation_water_ingress_ward", "probability": 0.76, "assumption": true}
        ]
    },
    {
        "facility_id": "osm:shelter:digha_cyclone",
        "scenario_id": "amphan-2020-t-72h",
        "failure_probability": 0.20,
        "earliest_failure_time": "2020-05-20T11:00:00Z",
        "hours_of_warning": 71.0,
        "cause_chain": [
            {"node": "osm:shelter:digha_cyclone", "event": "high_tide_wave_runup_perimeter", "probability": 0.20, "assumption": false}
        ]
    },
    {
        "facility_id": "osm:telecom:digha_radar",
        "scenario_id": "amphan-2020-t-72h",
        "failure_probability": 0.42,
        "earliest_failure_time": "2020-05-20T07:00:00Z",
        "hours_of_warning": 67.0,
        "cause_chain": [
            {"node": "osm:substation:digha_33kv", "event": "direct_marine_surge_0.75m", "probability": 0.84, "assumption": false},
            {"node": "osm:telecom:digha_radar", "event": "switch_to_hardened_diesel_genset", "probability": 0.42, "assumption": true}
        ]
    },

    # Diamond Harbour & Canning
    {
        "facility_id": "osm:substation:diamond_33kv",
        "scenario_id": "amphan-2020-t-72h",
        "failure_probability": 0.65,
        "earliest_failure_time": "2020-05-20T08:30:00Z",
        "hours_of_warning": 68.5,
        "cause_chain": [
            {"node": "osm:substation:diamond_33kv", "event": "hooghly_river_tidal_bore_0.52m", "probability": 0.65, "assumption": false}
        ]
    },
    {
        "facility_id": "osm:hospital:diamond_harbour",
        "scenario_id": "amphan-2020-t-72h",
        "failure_probability": 0.52,
        "earliest_failure_time": "2020-05-20T13:00:00Z",
        "hours_of_warning": 73.0,
        "cause_chain": [
            {"node": "osm:substation:diamond_33kv", "event": "hooghly_river_tidal_bore_0.52m", "probability": 0.65, "assumption": false},
            {"node": "osm:hospital:diamond_harbour", "event": "standby_diesel_engaged", "probability": 0.52, "assumption": true}
        ]
    },
    {
        "facility_id": "osm:substation:canning_33kv",
        "scenario_id": "amphan-2020-t-72h",
        "failure_probability": 0.78,
        "earliest_failure_time": "2020-05-20T07:15:00Z",
        "hours_of_warning": 67.2,
        "cause_chain": [
            {"node": "osm:substation:canning_33kv", "event": "matla_river_surge_0.68m", "probability": 0.78, "assumption": false}
        ]
    },
    {
        "facility_id": "osm:shelter:canning_relief",
        "scenario_id": "amphan-2020-t-72h",
        "failure_probability": 0.32,
        "earliest_failure_time": "2020-05-20T11:30:00Z",
        "hours_of_warning": 71.5,
        "cause_chain": [
            {"node": "osm:shelter:canning_relief", "event": "perimeter_embankment_seepage", "probability": 0.32, "assumption": true}
        ]
    },

    # Sundarbans / Gosaba & Basirhat
    {
        "facility_id": "osm:substation:gosaba_solar",
        "scenario_id": "amphan-2020-t-72h",
        "failure_probability": 0.89,
        "earliest_failure_time": "2020-05-20T06:45:00Z",
        "hours_of_warning": 66.8,
        "cause_chain": [
            {"node": "osm:substation:gosaba_solar", "event": "delta_saline_inundation_0.71m", "probability": 0.89, "assumption": false}
        ]
    },
    {
        "facility_id": "osm:shelter:gosaba_island",
        "scenario_id": "amphan-2020-t-72h",
        "failure_probability": 0.38,
        "earliest_failure_time": "2020-05-20T10:30:00Z",
        "hours_of_warning": 70.5,
        "cause_chain": [
            {"node": "osm:substation:gosaba_solar", "event": "delta_saline_inundation_0.71m", "probability": 0.89, "assumption": false},
            {"node": "osm:shelter:gosaba_island", "event": "island_isolation_jetty_submerged", "probability": 0.38, "assumption": true}
        ]
    },
    {
        "facility_id": "osm:hospital:basirhat_district",
        "scenario_id": "amphan-2020-t-72h",
        "failure_probability": 0.34,
        "earliest_failure_time": "2020-05-20T15:00:00Z",
        "hours_of_warning": 75.0,
        "cause_chain": [
            {"node": "osm:hospital:basirhat_district", "event": "drainage_choke_heavy_rain", "probability": 0.34, "assumption": false}
        ]
    },
    {
        "facility_id": "osm:shelter:hingalganj",
        "scenario_id": "amphan-2020-t-72h",
        "failure_probability": 0.44,
        "earliest_failure_time": "2020-05-20T09:45:00Z",
        "hours_of_warning": 69.8,
        "cause_chain": [
            {"node": "osm:shelter:hingalganj", "event": "icnamati_river_wave_breach", "probability": 0.44, "assumption": true}
        ]
    },

    # Bakkhali & Frazerganj
    {
        "facility_id": "osm:substation:frazerganj_33kv",
        "scenario_id": "amphan-2020-t-72h",
        "failure_probability": 0.91,
        "earliest_failure_time": "2020-05-20T05:15:00Z",
        "hours_of_warning": 65.2,
        "cause_chain": [
            {"node": "osm:substation:frazerganj_33kv", "event": "marine_surge_direct_strike_0.82m", "probability": 0.91, "assumption": false}
        ]
    },
    {
        "facility_id": "osm:shelter:bakkhali_tourist",
        "scenario_id": "amphan-2020-t-72h",
        "failure_probability": 0.28,
        "earliest_failure_time": "2020-05-20T09:00:00Z",
        "hours_of_warning": 69.0,
        "cause_chain": [
            {"node": "osm:substation:frazerganj_33kv", "event": "marine_surge_direct_strike_0.82m", "probability": 0.91, "assumption": false},
            {"node": "osm:shelter:bakkhali_tourist", "event": "coastal_roadway_cutoff", "probability": 0.28, "assumption": true}
        ]
    }
]

all_risks = existing_risks + [r for r in new_risks if r["facility_id"] not in existing_risk_ids]
(GOLDEN_DIR / "risks.json").write_text(json.dumps(all_risks, indent=2), encoding="utf-8")
print(f"Total risks updated: {len(all_risks)}")

# 4. Update edges.json
existing_edges = json.loads((GOLDEN_DIR / "edges.json").read_text(encoding="utf-8"))
new_edges = [
    {"from_node": "osm:substation:cesc_central", "to_node": "osm:hospital:sskm", "dependency_type": "power", "assumption": True, "criticality": "high"},
    {"from_node": "osm:substation:cesc_central", "to_node": "osm:telecom:kolkata_hub", "dependency_type": "power", "assumption": True, "criticality": "critical"},
    {"from_node": "osm:substation:haldia_grid", "to_node": "osm:hospital:haldia_port", "dependency_type": "power", "assumption": True, "criticality": "critical"},
    {"from_node": "osm:substation:digha_33kv", "to_node": "osm:hospital:digha_state", "dependency_type": "power", "assumption": True, "criticality": "critical"},
    {"from_node": "osm:substation:digha_33kv", "to_node": "osm:telecom:digha_radar", "dependency_type": "power", "assumption": True, "criticality": "critical"},
    {"from_node": "osm:substation:diamond_33kv", "to_node": "osm:hospital:diamond_harbour", "dependency_type": "power", "assumption": True, "criticality": "high"},
    {"from_node": "osm:substation:canning_33kv", "to_node": "osm:shelter:canning_relief", "dependency_type": "power", "assumption": True, "criticality": "medium"},
    {"from_node": "osm:substation:gosaba_solar", "to_node": "osm:shelter:gosaba_island", "dependency_type": "power", "assumption": True, "criticality": "high"},
    {"from_node": "osm:substation:frazerganj_33kv", "to_node": "osm:shelter:bakkhali_tourist", "dependency_type": "power", "assumption": True, "criticality": "high"},
    {"from_node": "osm:bridge:haldi_river", "to_node": "osm:hospital:haldia_port", "dependency_type": "transport", "assumption": True, "criticality": "high"}
]

all_edges = existing_edges + new_edges
(GOLDEN_DIR / "edges.json").write_text(json.dumps(all_edges, indent=2), encoding="utf-8")
print(f"Total edges updated: {len(all_edges)}")
