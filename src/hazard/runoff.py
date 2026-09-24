"""Rainfall Runoff & Drainage Accumulation Routing Module.

Routes precipitation volume down the D8 flow accumulation network,
calculating local pluvial ponding depths in low-lying agricultural depressions
and estuarine drainage bottlenecks.
"""

from typing import Dict
import numpy as np


class RainfallRunoffModel:
    """Routes surface precipitation runoff across the terrain elevation and flow network."""

    def __init__(self, runoff_coefficient: float = 0.65):
        # 0.65 represents heavy delta clay and saturated coastal alluvium
        self.c_runoff = runoff_coefficient

    def compute_ponding_depth(
        self,
        rainfall_mm: np.ndarray,
        elevation_m: np.ndarray,
        flow_accumulation: np.ndarray,
        sea_mask: np.ndarray,
    ) -> Dict[str, np.ndarray]:
        """Calculate localized pluvial rainfall ponding depth (meters)."""
        # Base runoff volume in meters
        rainfall_m = rainfall_mm * 1e-3
        direct_runoff = rainfall_m * self.c_runoff

        # Flow accumulation multiplier (water gathers in drainage channels)
        accum_factor = 1.0 + 0.12 * np.log1p(flow_accumulation)
        
        # Depression sink factor: low-lying land below 2.5m elevation accumulates deeper water
        lowland_multiplier = np.clip(1.0 + (2.5 - elevation_m) * 0.4, 1.0, 2.5)

        rain_depth = direct_runoff * accum_factor * lowland_multiplier
        # Sea cells do not accumulate land ponding
        rain_depth[sea_mask == 1] = 0.0
        rain_depth = np.maximum(0.0, rain_depth)

        return {
            "direct_runoff_m": direct_runoff,
            "rain_ponding_depth_m": rain_depth,
        }
