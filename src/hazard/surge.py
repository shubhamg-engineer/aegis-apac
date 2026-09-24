"""Coastal Water Level & Storm Surge Calculation Module.

Computes coastal sea surface heights by combining the inverse barometer effect,
shallow continental shelf wind setup, and astronomical tide baselines.
"""

from typing import Dict
import numpy as np


class StormSurgeModel:
    """Calculates coastal water level boundary conditions for storm surge."""

    def __init__(
        self,
        ambient_pressure_hpa: float = 1013.25,
        water_density_kg_m3: float = 1025.0,
        gravity_ms2: float = 9.80665,
        shelf_width_km: float = 120.0,
        shelf_mean_depth_m: float = 25.0,
        astronomical_tide_baseline_m: float = 1.8,
        surge_calibration_factor: float = 1.15,
    ):
        self.Pn = ambient_pressure_hpa
        self.rho_w = water_density_kg_m3
        self.g = gravity_ms2
        self.L_shelf = shelf_width_km * 1000.0
        self.D_shelf = shelf_mean_depth_m
        self.tide_m = astronomical_tide_baseline_m
        self.calib_factor = surge_calibration_factor

    def compute_drag_coefficient(self, wind_speed_ms: np.ndarray) -> np.ndarray:
        """Wu (1982) surface drag coefficient formulation for hurricane winds."""
        cd = (0.8 + 0.065 * wind_speed_ms) * 1e-3
        return np.clip(cd, 0.001, 0.0032)

    def compute_coastal_water_level(
        self,
        pressure_hpa: np.ndarray,
        wind_speed_ms: np.ndarray,
        surge_multiplier: float = None,
    ) -> Dict[str, np.ndarray]:
        """Compute the inverse barometer, wind setup, and total coastal sea level."""
        factor = surge_multiplier if surge_multiplier is not None else self.calib_factor
        
        # 1. Inverse Barometer Effect: ~1 cm per hPa pressure deficit
        pressure_deficit_hpa = np.maximum(0.0, self.Pn - pressure_hpa)
        delta_p_pa = pressure_deficit_hpa * 100.0
        eta_ib = delta_p_pa / (self.rho_w * self.g)  # meters
        
        # 2. Wind Setup: tau_w = rho_air * Cd * V^2
        rho_air = 1.15
        cd = self.compute_drag_coefficient(wind_speed_ms)
        tau_w = rho_air * cd * (wind_speed_ms ** 2)
        
        # Steady-state shallow shelf setup: eta = (tau_w * L) / (rho_w * g * D)
        eta_wind = factor * (tau_w * self.L_shelf) / (self.rho_w * self.g * self.D_shelf)
        
        # 3. Total Coastal Water Level = IB + Wind Setup + Tide
        total_water_level = eta_ib + eta_wind + self.tide_m

        return {
            "eta_ib_m": eta_ib,
            "eta_wind_m": eta_wind,
            "astronomical_tide_m": np.full_like(eta_ib, self.tide_m),
            "total_coastal_water_level_m": total_water_level,
        }
