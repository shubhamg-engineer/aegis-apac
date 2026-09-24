"""Aegis-APAC Ensemble Hazard Generator and Probability Aggregator.

Generates 30-50 perturbed cyclone ensemble members based on IMD North Indian Ocean
forecast-error statistics (Mohapatra et al., 2021) and computes pixel-wise
exceedance probabilities:
    P(depth > 0.3m)
    P(depth > 1.0m)
and earliest exceedance time (T_first).
"""

import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from src.hazard.engine import HazardEngine


# Official IMD North Indian Ocean error statistics at 24h, 48h, 72h lead times
# Citation: Mohapatra et al., "Verification of cyclone track and intensity forecasts
# over the North Indian Ocean", Mausam / IMD Annual Cyclone Report.
IMD_ERROR_STATS = {
    72: {"along_track_km": 50.0, "cross_track_km": 40.0, "pc_hpa": 8.0, "rmw_km": 10.0},
    48: {"along_track_km": 30.0, "cross_track_km": 25.0, "pc_hpa": 5.0, "rmw_km": 8.0},
    24: {"along_track_km": 15.0, "cross_track_km": 12.0, "pc_hpa": 3.0, "rmw_km": 5.0},
    12: {"along_track_km": 10.0, "cross_track_km": 8.0, "pc_hpa": 2.0, "rmw_km": 4.0},
    0:  {"along_track_km": 5.0,  "cross_track_km": 4.0,  "pc_hpa": 1.0, "rmw_km": 2.0},
}


class EnsembleHazardGenerator:
    """Generates perturbed cyclone realizations and aggregates probabilistic hazard metrics."""

    def __init__(
        self,
        num_members: int = 40,
        random_seed: int = 42,
        hazard_engine: Optional[HazardEngine] = None,
    ):
        self.num_members = num_members
        self.random_seed = random_seed
        self.hazard_engine = hazard_engine or HazardEngine()
        self.rng = np.random.default_rng(random_seed)

    def get_lead_time_errors(self, lead_time_hours: float) -> Dict[str, float]:
        """Interpolate IMD error statistics based on forecast lead time."""
        lt = max(0.0, min(72.0, lead_time_hours))
        keys = sorted(IMD_ERROR_STATS.keys())
        for i in range(len(keys) - 1):
            k1, k2 = keys[i], keys[i + 1]
            if k1 <= lt <= k2:
                fraction = (lt - k1) / (k2 - k1) if k2 > k1 else 0.0
                return {
                    param: IMD_ERROR_STATS[k1][param] + fraction * (IMD_ERROR_STATS[k2][param] - IMD_ERROR_STATS[k1][param])
                    for param in ["along_track_km", "cross_track_km", "pc_hpa", "rmw_km"]
                }
        return IMD_ERROR_STATS[72]

    def generate_member_parameters(
        self,
        center_lon: float,
        center_lat: float,
        motion_bearing_deg: float,
        base_pc_hpa: float,
        base_vmax_ms: float,
        base_rmw_km: float,
        lead_time_hours: float = 72.0,
    ) -> List[Dict[str, float]]:
        """Generate N perturbed ensemble member parameter dictionaries."""
        errs = self.get_lead_time_errors(lead_time_hours)
        members: List[Dict[str, float]] = []

        # Convert bearing to radians and along/cross unit vectors
        theta = np.radians(motion_bearing_deg)
        along_unit = np.array([np.sin(theta), np.cos(theta)])  # (dlon, dlat) in km
        cross_unit = np.array([-np.cos(theta), np.sin(theta)])

        km_per_deg_lat = 111.0
        km_per_deg_lon = 111.0 * np.cos(np.radians(center_lat))

        # Member 0 is deterministic unperturbed reference
        members.append({
            "member_id": 0,
            "center_lon": center_lon,
            "center_lat": center_lat,
            "Pc": base_pc_hpa,
            "Vmax_ms": base_vmax_ms,
            "Rmax_km": base_rmw_km,
            "along_pert_km": 0.0,
            "cross_pert_km": 0.0,
            "pc_pert_hpa": 0.0,
        })

        for m in range(1, self.num_members):
            # Normal distribution with standard deviation = error_stat / 1.96 (95% CI)
            along_pert = self.rng.normal(0, errs["along_track_km"] / 1.96)
            cross_pert = self.rng.normal(0, errs["cross_track_km"] / 1.96)
            pc_pert = self.rng.normal(0, errs["pc_hpa"] / 1.96)
            rmw_pert = self.rng.normal(0, errs["rmw_km"] / 1.96)

            # Displace coordinates
            delta_km = along_pert * along_unit + cross_pert * cross_unit
            d_lon = delta_km[0] / km_per_deg_lon
            d_lat = delta_km[1] / km_per_deg_lat

            p_c = max(890.0, min(1005.0, base_pc_hpa + pc_pert))
            r_max = max(15.0, min(80.0, base_rmw_km + rmw_pert))

            # Adjust Vmax dynamically according to central pressure drop (empirical Atkinson-Holliday)
            # delta_V = sqrt((base_Pc - perturbed_Pc) * constant)
            pressure_drop = max(0.0, 1010.0 - p_c)
            v_max = max(20.0, min(75.0, 3.4 * (pressure_drop ** 0.644)))

            members.append({
                "member_id": m,
                "center_lon": float(center_lon + d_lon),
                "center_lat": float(center_lat + d_lat),
                "Pc": float(p_c),
                "Vmax_ms": float(v_max),
                "Rmax_km": float(r_max),
                "along_pert_km": float(along_pert),
                "cross_pert_km": float(cross_pert),
                "pc_pert_hpa": float(pc_pert),
            })

        return members

    def run_ensemble_timestep(
        self,
        lons: np.ndarray,
        lats: np.ndarray,
        elevation_m: np.ndarray,
        sea_mask: np.ndarray,
        flow_accumulation: np.ndarray,
        rainfall_mm: np.ndarray,
        members_params: List[Dict[str, float]],
    ) -> Dict[str, Any]:
        """Run all members for a single timestep and compute exceedance probabilities."""
        t_start = time.perf_counter()
        n_members = len(members_params)
        h, w = elevation_m.shape

        member_depths = np.zeros((n_members, h, w), dtype=np.float32)

        for i, m_param in enumerate(members_params):
            res = self.hazard_engine.run_time_step(
                lons=lons,
                lats=lats,
                elevation_m=elevation_m,
                sea_mask=sea_mask,
                flow_accumulation=flow_accumulation,
                rainfall_mm=rainfall_mm,
                center_lon=m_param["center_lon"],
                center_lat=m_param["center_lat"],
                Pc=m_param["Pc"],
                Vmax_ms=m_param["Vmax_ms"],
                Rmax_km=m_param["Rmax_km"],
            )
            member_depths[i] = res["total_depth_m"]

        # Compute exceedance probabilities
        prob_depth_03m = np.mean(member_depths >= 0.3, axis=0)
        prob_depth_10m = np.mean(member_depths >= 1.0, axis=0)

        # Strictly enforce monotonicity: P(depth > 1.0) <= P(depth > 0.3)
        prob_depth_10m = np.minimum(prob_depth_10m, prob_depth_03m)

        # Zero out sea mask cells
        prob_depth_03m[sea_mask == 1] = 0.0
        prob_depth_10m[sea_mask == 1] = 0.0

        p50_depth = np.median(member_depths, axis=0)
        p90_depth = np.percentile(member_depths, 90, axis=0)
        p50_depth[sea_mask == 1] = 0.0
        p90_depth[sea_mask == 1] = 0.0

        runtime_sec = time.perf_counter() - t_start

        return {
            "num_members": n_members,
            "prob_depth_03m": prob_depth_03m,
            "prob_depth_10m": prob_depth_10m,
            "p50_depth_m": p50_depth,
            "p90_depth_m": p90_depth,
            "member_depths": member_depths,
            "runtime_sec": runtime_sec,
        }

    def run_multi_timestep_ensemble(
        self,
        lons: np.ndarray,
        lats: np.ndarray,
        elevation_m: np.ndarray,
        sea_mask: np.ndarray,
        flow_accumulation: np.ndarray,
        timesteps_rainfall: Dict[int, np.ndarray],
        timesteps_track: Dict[int, Dict[str, float]],
        lead_time_at_landfall: float = 72.0,
    ) -> Dict[str, Any]:
        """Run full ensemble across multiple forecast timesteps and compute earliest exceedance."""
        t_total_start = time.perf_counter()
        sorted_steps = sorted(timesteps_track.keys())
        h, w = elevation_m.shape

        timestep_results: Dict[int, Dict[str, Any]] = {}
        earliest_exceedance_step = np.full((h, w), np.nan, dtype=np.float32)

        for step in sorted_steps:
            trk = timesteps_track[step]
            rf = timesteps_rainfall.get(step, np.zeros_like(elevation_m))
            # Lead time decreases as step approaches landfall (step <= 0)
            lead_time = max(0.0, lead_time_at_landfall + step)

            members_params = self.generate_member_parameters(
                center_lon=trk["center_lon"],
                center_lat=trk["center_lat"],
                motion_bearing_deg=trk.get("bearing_deg", 35.0),
                base_pc_hpa=trk["pc_hpa"],
                base_vmax_ms=trk["vmax_ms"],
                base_rmw_km=trk["rmw_km"],
                lead_time_hours=lead_time,
            )

            ts_res = self.run_ensemble_timestep(
                lons=lons,
                lats=lats,
                elevation_m=elevation_m,
                sea_mask=sea_mask,
                flow_accumulation=flow_accumulation,
                rainfall_mm=rf,
                members_params=members_params,
            )
            timestep_results[step] = ts_res

            # Update earliest exceedance time where P(depth >= 0.3m) >= 0.20 (20% ensemble threshold)
            exceeded_mask = (ts_res["prob_depth_03m"] >= 0.20) & np.isnan(earliest_exceedance_step)
            earliest_exceedance_step[exceeded_mask] = float(step)

        total_runtime_sec = time.perf_counter() - t_total_start

        return {
            "timesteps": sorted_steps,
            "results_by_timestep": timestep_results,
            "earliest_exceedance_step": earliest_exceedance_step,
            "total_runtime_sec": total_runtime_sec,
            "lead_time_at_landfall": lead_time_at_landfall,
            "num_members": self.num_members,
        }
