"""Aegis-APAC Infrastructure Cascade Engine.

Constructs directed infrastructure dependency graphs (power, access, and functional dependencies)
and simulates cascading failure propagation across perturbed ensemble realizations.
Computes failure probabilities, earliest failure timestamps, warning horizons, and
cause chains with explicit assumption tracking.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx
import numpy as np

from src.contracts import CauseEvent, Edge, EdgeRelation, Facility, FacilityType, RiskResult


DEFAULT_CASCADE_THRESHOLDS = {
    "substation_failure_depth_m": 0.4,
    "road_blockage_depth_light_vehicle_m": 0.3,
    "road_blockage_depth_heavy_vehicle_m": 0.6,
    "hospital_impairment_depth_m": 0.3,
    "hospital_default_backup_power_hours": 8.0,
    "shelter_unusable_depth_m": 0.15,
    "telecom_failure_depth_m": 0.5,
    "telecom_default_battery_hours": 4.0,
    "bridge_failure_depth_m": 0.6,
}


class CascadeEngine:
    """Simulates direct hazard impacts and secondary cascading infrastructure failures."""

    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        self.thresholds = dict(DEFAULT_CASCADE_THRESHOLDS)
        if thresholds:
            self.thresholds.update(thresholds)

    def build_graph(self, facilities: List[Facility], edges: List[Edge]) -> nx.DiGraph:
        """Construct directed dependency graph from facilities and structural links."""
        G = nx.DiGraph()

        for fac in facilities:
            G.add_node(
                fac.id,
                facility=fac,
                type=fac.type,
                name=fac.name,
                elevation_m=fac.elevation_m,
                attributes=fac.attributes,
                assumption_fields=fac.assumption_fields,
            )

        for edge in edges:
            G.add_edge(
                edge.from_node,
                edge.to_node,
                relation=edge.relation,
                assumption=edge.assumption,
            )

        return G

    def evaluate_direct_node_failure(
        self,
        node_id: str,
        facility_type: FacilityType,
        water_depth_m: float,
    ) -> Tuple[bool, Optional[str]]:
        """Evaluate direct physical failure at a facility due to local flood depth."""
        if facility_type == FacilityType.SUBSTATION:
            thresh = self.thresholds["substation_failure_depth_m"]
            if water_depth_m >= thresh:
                return True, f"Substation switchgear inundated by {water_depth_m:.2f}m (threshold >= {thresh}m)"

        elif facility_type == FacilityType.ROAD_SEGMENT:
            thresh = self.thresholds["road_blockage_depth_light_vehicle_m"]
            if water_depth_m >= thresh:
                return True, f"Roadway submerged under {water_depth_m:.2f}m floodwater (impassable >= {thresh}m)"

        elif facility_type == FacilityType.BRIDGE:
            thresh = self.thresholds["bridge_failure_depth_m"]
            if water_depth_m >= thresh:
                return True, f"Bridge approach road submerged under {water_depth_m:.2f}m floodwater (impassable >= {thresh}m)"

        elif facility_type == FacilityType.HOSPITAL:
            thresh = self.thresholds["hospital_impairment_depth_m"]
            if water_depth_m >= thresh:
                return True, f"Hospital ground floor/ER submerged under {water_depth_m:.2f}m floodwater"

        elif facility_type == FacilityType.SHELTER:
            thresh = self.thresholds["shelter_unusable_depth_m"]
            if water_depth_m >= thresh:
                return True, f"Cyclone shelter plinth flooded by {water_depth_m:.2f}m (unusable >= {thresh}m)"

        elif facility_type == FacilityType.TELECOM_TOWER:
            thresh = self.thresholds["telecom_failure_depth_m"]
            if water_depth_m >= thresh:
                return True, f"Telecom base transceiver electronics inundated by {water_depth_m:.2f}m"

        return False, None

    def simulate_member(
        self,
        G: nx.DiGraph,
        timesteps_hours: List[int],
        depth_by_step_and_node: Dict[int, Dict[str, float]],
    ) -> Dict[str, Dict[str, Any]]:
        """Simulate cascade failure progression for a single ensemble realization across timesteps.

        Returns a dictionary mapping node_id -> {
            "failed": bool,
            "failure_step_h": Optional[int],
            "failure_cause": Optional[str],
            "cause_chain": List[CauseEvent],
        }
        """
        # Node operational states
        node_state = {n: {"failed": False, "failure_step_h": None, "cause": None, "chain": []} for n in G.nodes}
        # Track when power was first lost to enforce generator/battery backup delay
        power_lost_step: Dict[str, Optional[int]] = {n: None for n in G.nodes}

        for step in sorted(timesteps_hours):
            depths_now = depth_by_step_and_node.get(step, {})

            # 1. Evaluate Direct Inundation Failures
            for node, data in G.nodes(data=True):
                if node_state[node]["failed"]:
                    continue

                fac_type = data["type"]
                depth = depths_now.get(node, 0.0)
                is_failed, cause_msg = self.evaluate_direct_node_failure(node, fac_type, depth)

                if is_failed:
                    node_state[node]["failed"] = True
                    node_state[node]["failure_step_h"] = step
                    node_state[node]["cause"] = cause_msg
                    node_state[node]["chain"].append(
                        CauseEvent(
                            node=node,
                            event=cause_msg or "Direct inundation failure",
                            probability=1.0,
                            assumption=True,
                        )
                    )

            # 2. Propagate Secondary Power & Access Cascades until convergence
            changed = True
            while changed:
                changed = False
                for node, data in G.nodes(data=True):
                    if node_state[node]["failed"]:
                        continue

                    fac_type = data["type"]
                    attrs = data.get("attributes", {})

                    # A. Check Power Dependencies (edges where other -> node with relation POWERS or DEPENDS_ON)
                    power_suppliers = [
                        u for u, v, edata in G.in_edges(node, data=True)
                        if edata.get("relation") in (EdgeRelation.POWERS, EdgeRelation.DEPENDS_ON)
                    ]

                    if power_suppliers:
                        all_power_lost = all(node_state[sup]["failed"] for sup in power_suppliers)
                        if all_power_lost:
                            if power_lost_step[node] is None:
                                power_lost_step[node] = step

                            # Check backup power duration
                            backup_hrs = float(
                                attrs.get(
                                    "backup_power_hours",
                                    self.thresholds["hospital_default_backup_power_hours"]
                                    if fac_type == FacilityType.HOSPITAL
                                    else self.thresholds["telecom_default_battery_hours"]
                                )
                            )
                            elapsed_outage_hrs = step - power_lost_step[node]

                            if elapsed_outage_hrs >= backup_hrs:
                                node_state[node]["failed"] = True
                                node_state[node]["failure_step_h"] = step
                                cause = f"Total power loss: backup generator/battery exhausted after {backup_hrs:.0f}h"
                                node_state[node]["cause"] = cause
                                # Record parent failures in chain
                                for sup in power_suppliers:
                                    if node_state[sup]["cause"]:
                                        node_state[node]["chain"].append(
                                            CauseEvent(
                                                node=sup,
                                                event=node_state[sup]["cause"],
                                                probability=1.0,
                                                assumption=True,
                                            )
                                        )
                                node_state[node]["chain"].append(
                                    CauseEvent(
                                        node=node,
                                        event=cause,
                                        probability=1.0,
                                        assumption=True,
                                    )
                                )
                                changed = True
                                continue
                        else:
                            # Power restored / active
                            power_lost_step[node] = None

                    # B. Check Access Dependencies (edges where road/bridge -> node with relation ACCESSES)
                    access_roads = [
                        u for u, v, edata in G.in_edges(node, data=True)
                        if edata.get("relation") == EdgeRelation.ACCESSES
                    ]

                    if access_roads and fac_type in (FacilityType.HOSPITAL, FacilityType.SHELTER):
                        all_roads_cut = all(node_state[r]["failed"] for r in access_roads)
                        if all_roads_cut:
                            node_state[node]["failed"] = True
                            node_state[node]["failure_step_h"] = step
                            cause = f"All incoming road access routes impassable ({len(access_roads)} routes cut)"
                            node_state[node]["cause"] = cause
                            for r in access_roads:
                                if node_state[r]["cause"]:
                                    node_state[node]["chain"].append(
                                        CauseEvent(
                                            node=r,
                                            event=node_state[r]["cause"],
                                            probability=1.0,
                                            assumption=True,
                                        )
                                    )
                            node_state[node]["chain"].append(
                                CauseEvent(
                                    node=node,
                                    event=cause,
                                    probability=1.0,
                                    assumption=True,
                                )
                            )
                            changed = True
                            continue

        return node_state

    def run_ensemble_cascade(
        self,
        facilities: List[Facility],
        edges: List[Edge],
        ensemble_depths_by_member: List[Dict[int, Dict[str, float]]],
        timesteps_hours: List[int],
        scenario_id: str = "amphan-2020",
        forecast_base_time: Optional[datetime] = None,
    ) -> List[RiskResult]:
        """Execute cascade across all ensemble members and generate validated RiskResult contracts."""
        G = self.build_graph(facilities, edges)
        n_members = len(ensemble_depths_by_member)
        if n_members == 0:
            return []

        base_time = forecast_base_time or datetime(2020, 5, 17, 12, 0, 0)
        # Landfall occurs at T-0h (e.g. 72h after forecast issue)
        landfall_time = base_time + timedelta(hours=72)

        member_results: List[Dict[str, Dict[str, Any]]] = []
        for mem_depths in ensemble_depths_by_member:
            res = self.simulate_member(G, timesteps_hours, mem_depths)
            member_results.append(res)

        risk_results: List[RiskResult] = []

        for node in G.nodes:
            failed_members = [res[node] for res in member_results if res[node]["failed"]]
            fail_count = len(failed_members)
            failure_prob = float(fail_count / n_members)

            if fail_count > 0:
                earliest_step = min(m["failure_step_h"] for m in failed_members if m["failure_step_h"] is not None)
                fail_timestamp = (landfall_time + timedelta(hours=earliest_step)).isoformat() + "Z"
                # Hours from forecast base time to earliest failure
                hours_of_warning = max(0.0, float((landfall_time + timedelta(hours=earliest_step) - base_time).total_seconds() / 3600.0))

                # Identify most frequent cause chain
                longest_chain = max((m["chain"] for m in failed_members), key=len, default=[])
                # Deduplicate chain while maintaining order
                seen_events: Set[str] = set()
                deduped_chain: List[CauseEvent] = []
                for ev in longest_chain:
                    key = f"{ev.node}:{ev.event}"
                    if key not in seen_events:
                        seen_events.add(key)
                        deduped_chain.append(
                            CauseEvent(
                                node=ev.node,
                                event=ev.event,
                                probability=round(failure_prob, 3),
                                assumption=True,
                            )
                        )
            else:
                fail_timestamp = (landfall_time + timedelta(hours=timesteps_hours[-1] if timesteps_hours else 6)).isoformat() + "Z"
                hours_of_warning = 72.0 + (timesteps_hours[-1] if timesteps_hours else 6)
                deduped_chain = []

            risk_results.append(
                RiskResult(
                    facility_id=node,
                    scenario_id=scenario_id,
                    failure_probability=round(failure_prob, 3),
                    earliest_failure_time=fail_timestamp,
                    hours_of_warning=round(hours_of_warning, 1),
                    cause_chain=deduped_chain,
                )
            )

        # Sort ranked facility list: highest failure probability first, then lowest hours of warning
        risk_results.sort(key=lambda r: (-r.failure_probability, r.hours_of_warning))
        return risk_results
