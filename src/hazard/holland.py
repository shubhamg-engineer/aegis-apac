"""Holland (1980) Parametric Cyclone Wind & Pressure Profile Module.

Computes 2D surface pressure fields and gradient wind velocity vectors
from cyclone track parameters (Pc, Vmax, Rmax, translation velocity).
"""

import math
from typing import Dict, Tuple
import numpy as np


class HollandProfile:
    """Calculates spatial atmospheric pressure and cyclostrophic gradient wind fields."""

    def __init__(
        self,
        ambient_pressure_hpa: float = 1013.25,
        air_density_kg_m3: float = 1.15,
        earth_angular_vel: float = 7.292115e-5,
    ):
        self.Pn = ambient_pressure_hpa
        self.rho = air_density_kg_m3
        self.omega = earth_angular_vel

    def compute_b_parameter(self, Pc: float, Vmax_ms: float, Rmax_km: float) -> float:
        """Estimate Holland B parameter from central pressure and peak wind."""
        delta_p = max(10.0, (self.Pn - Pc) * 100.0)  # Pa
        # Holland empirical relation: Vmax ~= sqrt(B * delta_p / rho)
        B = (Vmax_ms ** 2) * self.rho / delta_p
        return float(np.clip(B, 1.1, 2.2))

    def evaluate_grid(
        self,
        lons: np.ndarray,
        lats: np.ndarray,
        center_lon: float,
        center_lat: float,
        Pc: float,
        Vmax_ms: float,
        Rmax_km: float,
        forward_speed_ms: float = 6.0,
        heading_deg: float = 25.0,  # North-Northeastward track typical of Amphan
    ) -> Dict[str, np.ndarray]:
        """Compute 2D wind speed and atmospheric pressure grids."""
        xx, yy = np.meshgrid(lons, lats)
        
        # Distance (km) and bearing from cyclone center
        dx_km = (xx - center_lon) * 111.320 * np.cos(np.radians(yy))
        dy_km = (yy - center_lat) * 110.574
        r_km = np.sqrt(dx_km ** 2 + dy_km ** 2)
        r_km = np.maximum(0.5, r_km)  # Prevent zero division at eye center
        
        # Coriolis parameter f = 2 * omega * sin(lat)
        f_coriolis = 2.0 * self.omega * np.sin(np.radians(yy))
        
        # Pressure deficit in Pascals
        delta_p_pa = (self.Pn - Pc) * 100.0
        B = self.compute_b_parameter(Pc, Vmax_ms, Rmax_km)
        
        # Radial pressure profile: P(r) = Pc + (Pn - Pc) * exp(-(Rmax / r)^B)
        exponent = -((Rmax_km / r_km) ** B)
        pressure_hpa = Pc + (self.Pn - Pc) * np.exp(exponent)
        
        # Radial gradient wind velocity: Vg(r)
        term1 = (B / self.rho) * ((Rmax_km / r_km) ** B) * delta_p_pa * np.exp(exponent)
        term2 = ((r_km * 1000.0 * f_coriolis) / 2.0) ** 2
        vg = np.sqrt(np.maximum(0.0, term1 + term2)) - (r_km * 1000.0 * np.abs(f_coriolis)) / 2.0
        
        # Add forward speed asymmetry (right front quadrant enhancement)
        azimuth_rad = np.arctan2(dy_km, dx_km)
        heading_rad = np.radians(heading_deg)
        asym = 0.5 * forward_speed_ms * np.cos(azimuth_rad - heading_rad + np.pi / 2.0)
        total_wind_speed_ms = np.maximum(0.0, vg + asym)

        return {
            "pressure_hpa": pressure_hpa,
            "wind_speed_ms": total_wind_speed_ms,
            "distance_to_eye_km": r_km,
        }
