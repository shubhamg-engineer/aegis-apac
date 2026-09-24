"""Hazard Engine Calibration Module.

Performs parameter grid search against observed high-water marks and satellite
flood references (Copernicus EMS EMSR439) to find optimal surge and attenuation
factors.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Tuple
import numpy as np

from src.hazard.engine import HazardEngine


@dataclass
class CalibrationResult:
    surge_multiplier: float
    inland_decay_rate: float
    iou: float
    precision: float
    recall: float
    f1_score: float


class HazardCalibrator:
    """Calibrates surge multiplier and inland attenuation decay coefficients."""

    def __init__(
        self,
        candidate_multipliers: List[float] = [0.9, 1.0, 1.15, 1.3],
        candidate_decays: List[float] = [0.00012, 0.00018, 0.00025],
    ):
        self.multipliers = candidate_multipliers
        self.decays = candidate_decays

    def evaluate_metrics(self, predicted_mask: np.ndarray, reference_mask: np.ndarray) -> Tuple[float, float, float, float]:
        """Compute IoU (Jaccard), Precision, Recall, and F1."""
        intersection = np.logical_and(predicted_mask, reference_mask).sum()
        union = np.logical_or(predicted_mask, reference_mask).sum()
        pred_sum = predicted_mask.sum()
        ref_sum = reference_mask.sum()

        iou = float(intersection / union) if union > 0 else 0.0
        precision = float(intersection / pred_sum) if pred_sum > 0 else 0.0
        recall = float(intersection / ref_sum) if ref_sum > 0 else 0.0
        f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        return iou, precision, recall, f1

    def run_grid_search(
        self,
        lons: np.ndarray,
        lats: np.ndarray,
        elevation_m: np.ndarray,
        sea_mask: np.ndarray,
        flow_accumulation: np.ndarray,
        rainfall_mm: np.ndarray,
        landfall_pt: Dict[str, Any],
        reference_flood_mask: np.ndarray,
    ) -> Dict[str, Any]:
        """Execute grid search across candidate parameters."""
        engine = HazardEngine()
        results: List[CalibrationResult] = []
        best_res: CalibrationResult = None

        for mult in self.multipliers:
            for decay in self.decays:
                res = engine.run_time_step(
                    lons=lons,
                    lats=lats,
                    elevation_m=elevation_m,
                    sea_mask=sea_mask,
                    flow_accumulation=flow_accumulation,
                    rainfall_mm=rainfall_mm,
                    center_lon=landfall_pt["longitude"],
                    center_lat=landfall_pt["latitude"],
                    Pc=landfall_pt["central_pressure_hpa"],
                    Vmax_ms=landfall_pt["max_sustained_wind_ms"],
                    Rmax_km=landfall_pt["radius_max_winds_km"],
                    surge_multiplier=mult,
                    inland_decay_rate=decay,
                )

                # Land flood prediction where depth > 0.3m
                pred_mask = (res["total_depth_m"] > 0.3) & (sea_mask == 0)
                iou, prec, rec, f1 = self.evaluate_metrics(pred_mask, reference_flood_mask)

                entry = CalibrationResult(
                    surge_multiplier=mult,
                    inland_decay_rate=decay,
                    iou=round(iou, 3),
                    precision=round(prec, 3),
                    recall=round(rec, 3),
                    f1_score=round(f1, 3),
                )
                results.append(entry)

                if best_res is None or entry.iou > best_res.iou:
                    best_res = entry

        return {
            "optimal": asdict(best_res),
            "all_trials": [asdict(r) for r in results],
        }
