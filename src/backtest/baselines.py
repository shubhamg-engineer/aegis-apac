"""Aegis-APAC Benchmark Baselines for Comparative Backtesting.

Implements standard operational and naive baseline models:
1. Baseline 1 (B1): Static elevation threshold (< 3.0m).
2. Baseline 2 (B2): Deterministic single-run without infrastructure cascade.
"""

from typing import Any, Dict, List
import numpy as np

from src.contracts import Facility, RiskResult


class BaselineModels:
    """Computes comparative baseline performance for cyclone impact forecasting."""

    @staticmethod
    def run_b1_static_elevation(
        facilities: List[Facility],
        elevation_threshold_m: float = 3.0,
    ) -> List[Dict[str, Any]]:
        """Baseline 1: Static elevation threshold (< 3.0m).

        Flags every asset below 3m elevation as compromised regardless of storm track,
        surge dynamics, or inland hydraulic connectivity.
        """
        results = []
        for fac in facilities:
            is_compromised = fac.elevation_m < elevation_threshold_m
            results.append({
                "facility_id": fac.id,
                "model": "B1_Static_Elevation_3m",
                "predicted_failure": is_compromised,
                "failure_probability": 1.0 if is_compromised else 0.0,
                "lead_time_warning_hours": 0.0,  # Static threshold provides zero dynamic lead time
                "cause": "Static elevation below 3.0m baseline contour",
            })
        return results

    @staticmethod
    def run_b2_deterministic_single_run(
        facilities: List[Facility],
        deterministic_flood_depths: Dict[str, float],
        failure_threshold_m: float = 0.4,
    ) -> List[Dict[str, Any]]:
        """Baseline 2: Deterministic single-run without cascade.

        Evaluates direct inundation on a single forecast track without ensemble
        uncertainty and ignores secondary power/road dependencies.
        """
        results = []
        for fac in facilities:
            depth = deterministic_flood_depths.get(fac.id, 0.0)
            is_failed = depth >= failure_threshold_m
            results.append({
                "facility_id": fac.id,
                "model": "B2_Deterministic_No_Cascade",
                "predicted_failure": is_failed,
                "failure_probability": 1.0 if is_failed else 0.0,
                "lead_time_warning_hours": 6.0 if is_failed else 0.0,
                "cause": f"Direct inundation ({depth:.2f}m >= {failure_threshold_m}m)" if is_failed else "Dry",
            })
        return results
