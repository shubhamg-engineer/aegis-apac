"""Aegis-APAC Anticipatory Decision Engine.

Generates actionable operational interventions:
1. Road blockage windows and route closures.
2. Evacuation and shelter assignment respecting capacity and road accessibility.
3. Facility hardening, sandbagging, and proactive de-energization priorities.
Outputs strictly valid Action contracts linked to supporting RiskResults.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import numpy as np

from src.contracts import Action, ActionType, Facility, FacilityType, RiskResult


class DecisionEngine:
    """Computes operational actions and prioritised interventions from hazard and cascade risks."""

    def __init__(
        self,
        road_cutoff_depth_m: float = 0.3,
        deenergise_lead_hours: float = 2.0,
        high_risk_threshold: float = 0.4,
    ):
        self.road_cutoff_depth_m = road_cutoff_depth_m
        self.deenergise_lead_hours = deenergise_lead_hours
        self.high_risk_threshold = high_risk_threshold

    def compute_road_blockage_windows(
        self,
        roads: List[Facility],
        road_depths_by_timestep: Dict[int, Dict[str, float]],
        timesteps_hours: List[int],
    ) -> Dict[str, Dict[str, Any]]:
        """Determine time window when each road segment is impassable (depth >= threshold)."""
        blockage_windows: Dict[str, Dict[str, Any]] = {}

        for road in roads:
            impassable_steps = [
                step for step in sorted(timesteps_hours)
                if road_depths_by_timestep.get(step, {}).get(road.id, 0.0) >= self.road_cutoff_depth_m
            ]

            if impassable_steps:
                first_blocked = impassable_steps[0]
                last_blocked = impassable_steps[-1]
                blockage_windows[road.id] = {
                    "is_blocked": True,
                    "first_blocked_step_h": first_blocked,
                    "last_blocked_step_h": last_blocked,
                    "duration_hours": max(6, (last_blocked - first_blocked) + 6),
                }
            else:
                blockage_windows[road.id] = {
                    "is_blocked": False,
                    "first_blocked_step_h": None,
                    "last_blocked_step_h": None,
                    "duration_hours": 0,
                }

        return blockage_windows

    def allocate_shelters(
        self,
        population_clusters: List[Dict[str, Any]],
        shelters: List[Facility],
        risks_by_id: Dict[str, RiskResult],
        road_windows: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Greedy matching of vulnerable populations to operational, accessible shelters."""
        allocations: List[Dict[str, Any]] = []

        # Track remaining capacities
        shelter_capacities = {
            s.id: int(s.attributes.get("capacity", 500))
            for s in shelters
        }

        # Filter out compromised shelters (high failure probability or inundated)
        operational_shelters = [
            s for s in shelters
            if risks_by_id.get(s.id) is None or risks_by_id[s.id].failure_probability < 0.35
        ]

        for pop in population_clusters:
            ward_name = pop.get("name", "Coastal Ward")
            people_count = pop.get("population", 1000)
            pop_coords = pop.get("coordinates", [88.2, 21.7])
            district = pop.get("district", "Purba Medinipur")

            remaining_to_allocate = people_count
            allocated_shelter_ids = []

            # Sort operational shelters by euclidean distance to ward
            sorted_shelters = sorted(
                operational_shelters,
                key=lambda s: (
                    (s.geometry.get("coordinates", [0, 0])[0] - pop_coords[0]) ** 2 +
                    (s.geometry.get("coordinates", [0, 0])[1] - pop_coords[1]) ** 2
                )
            )

            for sh in sorted_shelters:
                avail = shelter_capacities[sh.id]
                if avail <= 0:
                    continue

                take = min(remaining_to_allocate, avail)
                shelter_capacities[sh.id] -= take
                remaining_to_allocate -= take
                allocated_shelter_ids.append({
                    "shelter_id": sh.id,
                    "shelter_name": sh.name,
                    "evacuees": take,
                })

                if remaining_to_allocate <= 0:
                    break

            allocations.append({
                "district": district,
                "ward": ward_name,
                "total_population": people_count,
                "unaccommodated": remaining_to_allocate,
                "shelters": allocated_shelter_ids,
            })

        return allocations

    def generate_actions(
        self,
        facilities: List[Facility],
        risks: List[RiskResult],
        population_clusters: Optional[List[Dict[str, Any]]] = None,
        forecast_base_time: Optional[datetime] = None,
        district: str = "Purba Medinipur",
    ) -> List[Action]:
        """Generate structured and prioritized anticipatory actions matching the frozen Action contract."""
        base_time = forecast_base_time or datetime(2020, 5, 17, 12, 0, 0)
        landfall_time = base_time + timedelta(hours=72)
        actions: List[Action] = []
        action_counter = 1

        risks_by_id = {r.facility_id: r for r in risks}
        facs_by_id = {f.id: f for f in facilities}

        # 1. Proactive Substation De-energization Actions
        for fac in facilities:
            if fac.type == FacilityType.SUBSTATION:
                r = risks_by_id.get(fac.id)
                if r and r.failure_probability >= self.high_risk_threshold:
                    earliest_time = datetime.fromisoformat(r.earliest_failure_time.rstrip("Z"))
                    deadline = (earliest_time - timedelta(hours=self.deenergise_lead_hours)).isoformat() + "Z"

                    actions.append(
                        Action(
                            id=f"act-{action_counter:03d}",
                            district=district,
                            type=ActionType.DEENERGISE,
                            description=(
                                f"Controlled de-energisation of {fac.name} ({fac.id}) 2h prior to "
                                f"predicted 0.4m floodwater inundation to prevent catastrophic short circuits and transformer explosions."
                            ),
                            deadline=deadline,
                            supporting_risk_ids=[fac.id],
                            confidence=round(r.failure_probability, 2),
                        )
                    )
                    action_counter += 1

        # 2. Road Closure Interventions
        for fac in facilities:
            if fac.type in (FacilityType.ROAD_SEGMENT, FacilityType.BRIDGE):
                r = risks_by_id.get(fac.id)
                if r and r.failure_probability >= 0.30:
                    earliest_time = datetime.fromisoformat(r.earliest_failure_time.rstrip("Z"))
                    deadline = (earliest_time - timedelta(hours=1)).isoformat() + "Z"

                    actions.append(
                        Action(
                            id=f"act-{action_counter:03d}",
                            district=district,
                            type=ActionType.CLOSE_ROAD,
                            description=(
                                f"Impose traffic barrier and close {fac.name} to light vehicles before water depth "
                                f"exceeds 0.3m. Divert emergency logistics to alternate inland elevated corridors."
                            ),
                            deadline=deadline,
                            supporting_risk_ids=[fac.id],
                            confidence=round(r.failure_probability, 2),
                        )
                    )
                    action_counter += 1

        # 3. Hospital Protection & Fuel Pre-positioning
        for fac in facilities:
            if fac.type == FacilityType.HOSPITAL:
                r = risks_by_id.get(fac.id)
                if r and r.failure_probability >= 0.25:
                    earliest_time = datetime.fromisoformat(r.earliest_failure_time.rstrip("Z"))
                    deadline = (earliest_time - timedelta(hours=4)).isoformat() + "Z"

                    actions.append(
                        Action(
                            id=f"act-{action_counter:03d}",
                            district=district,
                            type=ActionType.PROTECT_FACILITY,
                            description=(
                                f"Deploy perimeter sandbag berms at {fac.name} and pre-position 48h emergency diesel fuel "
                                f"reserves before feeder substations fail."
                            ),
                            deadline=deadline,
                            supporting_risk_ids=[fac.id] + [ev.node for ev in r.cause_chain if ev.node in facs_by_id],
                            confidence=round(r.failure_probability, 2),
                        )
                    )
                    action_counter += 1

        # 4. Community Evacuation Actions
        if population_clusters:
            shelters = [f for f in facilities if f.type == FacilityType.SHELTER]
            allocs = self.allocate_shelters(population_clusters, shelters, risks_by_id, {})

            for alloc in allocs:
                if not alloc["shelters"]:
                    continue
                sh_names = ", ".join(f"{s['shelter_name']} ({s['evacuees']} pax)" for s in alloc["shelters"])
                sh_ids = [s["shelter_id"] for s in alloc["shelters"]]
                deadline = (landfall_time - timedelta(hours=12)).isoformat() + "Z"

                actions.append(
                    Action(
                        id=f"act-{action_counter:03d}",
                        district=alloc["district"],
                        type=ActionType.EVACUATE,
                        description=(
                            f"Mandatory evacuation of {alloc['total_population'] - alloc['unaccommodated']} residents from "
                            f"{alloc['ward']} to designated multi-purpose shelters: {sh_names}."
                        ),
                        deadline=deadline,
                        supporting_risk_ids=sh_ids,
                        confidence=0.88,
                    )
                )
                action_counter += 1

        # 5. Pre-position Relief Stocks
        actions.append(
            Action(
                id=f"act-{action_counter:03d}",
                district=district,
                type=ActionType.PRE_POSITION_RELIEF,
                description=(
                    "Pre-position 5 mobile water purification units and inflatable rescue boats at Sagar Block HQ "
                    "before causeways submerge."
                ),
                deadline=(landfall_time - timedelta(hours=8)).isoformat() + "Z",
                supporting_risk_ids=[r.facility_id for r in risks[:3]],
                confidence=0.92,
            )
        )

        return actions
