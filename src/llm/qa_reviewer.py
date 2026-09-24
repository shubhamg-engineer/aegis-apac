"""Aegis-APAC Read-Only Visual QA Reviewer.

Flags potential spatial anomalies or inconsistencies between hazard rasters
and facility vulnerability evaluations for human operator review.
Hard Rule 1 Compliance: Strictly read-only; never overrides ground-truth values.
"""

from typing import Any, Dict, List
from src.contracts import Facility, RiskResult


class VisualQAReviewer:
    """Audits spatial consistency between hazard footprints and risk evaluations."""

    def review_consistency(
        self,
        facilities: List[Facility],
        risks: List[RiskResult],
        facility_flood_depths: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """Identify potential physical or logical contradictions for human operator review."""
        flags: List[Dict[str, Any]] = []
        risks_by_id = {r.facility_id: r for r in risks}

        for fac in facilities:
            depth = facility_flood_depths.get(fac.id, 0.0)
            risk = risks_by_id.get(fac.id)

            # Inconsistency Type 1: Facility inundated significantly (>0.5m) but reported 0% failure probability
            if depth >= 0.5 and (risk is None or risk.failure_probability == 0.0):
                flags.append({
                    "facility_id": fac.id,
                    "facility_name": fac.name,
                    "severity": "HIGH",
                    "issue": f"Facility experiences {depth:.2f}m flood depth but is marked with 0% failure risk.",
                    "recommendation": "Operator should inspect threshold settings or check for elevated plinth attribute.",
                    "override_permitted": False,
                })

            # Inconsistency Type 2: Road marked clear despite high inundation
            if fac.type.value in ("road_segment", "bridge") and depth >= 0.4 and (risk and risk.failure_probability < 0.2):
                flags.append({
                    "facility_id": fac.id,
                    "facility_name": fac.name,
                    "severity": "MEDIUM",
                    "issue": f"Roadway water level is {depth:.2f}m (above light vehicle limit) but risk is low ({risk.failure_probability}).",
                    "recommendation": "Verify embankment height or road clearance geometry.",
                    "override_permitted": False,
                })

            # Inconsistency Type 3: Negative hours of warning
            if risk and risk.hours_of_warning < 0.0:
                flags.append({
                    "facility_id": fac.id,
                    "facility_name": fac.name,
                    "severity": "HIGH",
                    "issue": f"Negative warning horizon ({risk.hours_of_warning}h) indicates failure occurred prior to forecast issue.",
                    "recommendation": "Check simulation baseline timestamp alignment.",
                    "override_permitted": False,
                })

        return flags
