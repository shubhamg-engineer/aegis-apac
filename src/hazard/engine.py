"""Aegis-APAC Integrated Hazard Engine.

Coordinates the Holland wind-pressure model, coastal surge water level calculation,
hydraulic connectivity inundation, and rainfall runoff routing to produce
multi-timestep combined flood depth rasters.
"""

from typing import Any, Dict, List, Optional
import numpy as np

from src.hazard.holland import HollandProfile
from src.hazard.inundation import HydraulicInundation
from src.hazard.runoff import RainfallRunoffModel
from src.hazard.surge import StormSurgeModel


class HazardEngine:
    """Integrated engine for storm surge, hydraulic inundation, and pluvial rainfall."""

    def __init__(
        self,
        surge_multiplier: float = 1.15,
        inland_decay_rate: float = 0.00018,
        astronomical_tide_m: float = 1.8,
    ):
        self.holland = HollandProfile()
        self.surge_model = StormSurgeModel(
            astronomical_tide_baseline_m=astronomical_tide_m,
            surge_calibration_factor=surge_multiplier,
        )
        self.inundation_model = HydraulicInundation(
            inland_attenuation_decay=inland_decay_rate
        )
        self.runoff_model = RainfallRunoffModel()

    def run_time_step(
        self,
        lons: np.ndarray,
        lats: np.ndarray,
        elevation_m: np.ndarray,
        sea_mask: np.ndarray,
        flow_accumulation: np.ndarray,
        rainfall_mm: np.ndarray,
        center_lon: float,
        center_lat: float,
        Pc: float,
        Vmax_ms: float,
        Rmax_km: float,
        surge_multiplier: Optional[float] = None,
        inland_decay_rate: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Compute full wind, pressure, surge, runoff, and total flood depth for a single time step."""
        # 1. Holland Wind & Pressure Field
        atm = self.holland.evaluate_grid(
            lons=lons,
            lats=lats,
            center_lon=center_lon,
            center_lat=center_lat,
            Pc=Pc,
            Vmax_ms=Vmax_ms,
            Rmax_km=Rmax_km,
        )

        # 2. Coastal Surge Water Level
        surge = self.surge_model.compute_coastal_water_level(
            pressure_hpa=atm["pressure_hpa"],
            wind_speed_ms=atm["wind_speed_ms"],
            surge_multiplier=surge_multiplier,
        )

        # 3. Overland Inundation with Hydraulic Connectivity
        inun = self.inundation_model.compute_inundation(
            coastal_water_level_m=surge["total_coastal_water_level_m"],
            elevation_m=elevation_m,
            sea_mask=sea_mask,
            inland_decay_rate=inland_decay_rate,
        )

        # 4. Rainfall Runoff Ponding
        runoff = self.runoff_model.compute_ponding_depth(
            rainfall_mm=rainfall_mm,
            elevation_m=elevation_m,
            flow_accumulation=flow_accumulation,
            sea_mask=sea_mask,
        )

        # 5. Combined Depth
        total_depth = inun["surge_depth_m"] + runoff["rain_ponding_depth_m"]
        total_depth[sea_mask == 1] = 0.0

        return {
            "pressure_hpa": atm["pressure_hpa"],
            "wind_speed_ms": atm["wind_speed_ms"],
            "coastal_water_level_m": surge["total_coastal_water_level_m"],
            "surge_depth_m": inun["surge_depth_m"],
            "rain_ponding_depth_m": runoff["rain_ponding_depth_m"],
            "total_depth_m": total_depth,
            "connected_flood_mask": inun["connected_flood_mask"],
        }
