"""Aegis-APAC Data Contracts (Frozen in Phase 1).

Standard Pydantic models and serialization schemas for all core entities:
Facility, Edge, RiskResult, Action, Advisory, Scenario, HazardLayer, Parametric.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FacilityType(str, Enum):
    SUBSTATION = "substation"
    HOSPITAL = "hospital"
    SHELTER = "shelter"
    TELECOM_TOWER = "telecom_tower"
    BRIDGE = "bridge"
    ROAD_SEGMENT = "road_segment"


class EdgeRelation(str, Enum):
    POWERS = "powers"
    SERVES = "serves"
    ACCESSES = "accesses"
    DEPENDS_ON = "depends_on"


class ActionType(str, Enum):
    EVACUATE = "evacuate"
    CLOSE_ROAD = "close_road"
    DEENERGISE = "deenergise"
    PROTECT_FACILITY = "protect_facility"
    PRE_POSITION_RELIEF = "pre_position_relief"


class AdvisoryRole(str, Enum):
    COLLECTOR = "collector"
    POWER_OPERATOR = "power_operator"
    CITIZENS = "citizens"


class AdvisoryStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    DISPATCHED = "dispatched"


class Facility(BaseModel):
    id: str = Field(..., description="Unique facility identifier, e.g. osm:node/123")
    type: FacilityType = Field(..., description="Classification of infrastructure")
    name: str = Field(..., description="Human-readable facility name")
    geometry: Dict[str, Any] = Field(..., description="GeoJSON Point or LineString geometry")
    elevation_m: float = Field(..., description="Ground elevation in meters")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Capacity, backup power, etc.")
    assumption_fields: List[str] = Field(default_factory=list, description="Attributes populated by assumption")


class Edge(BaseModel):
    from_node: str = Field(..., description="Origin node ID")
    to_node: str = Field(..., description="Destination node ID")
    relation: EdgeRelation = Field(..., description="Type of structural or functional link")
    assumption: bool = Field(True, description="True if link is inferred or estimated")


class CauseEvent(BaseModel):
    node: str = Field(..., description="Node where event occurs")
    event: str = Field(..., description="Event description, e.g. flooded, loses_grid_power")
    probability: float = Field(..., ge=0.0, le=1.0, description="Probability of this event")
    assumption: bool = Field(..., description="True if rule/event is an assumption")


class RiskResult(BaseModel):
    facility_id: str = Field(..., description="Target facility ID")
    scenario_id: str = Field(..., description="Associated forecast scenario ID")
    failure_probability: float = Field(..., ge=0.0, le=1.0, description="Ensemble probability of failure")
    earliest_failure_time: str = Field(..., description="Earliest expected failure ISO timestamp")
    hours_of_warning: float = Field(..., description="Hours from forecast to failure")
    cause_chain: List[CauseEvent] = Field(default_factory=list, description="Ordered chain of failure events")


class Action(BaseModel):
    id: str = Field(..., description="Action identifier, e.g. act-001")
    district: str = Field(..., description="Target administrative district")
    type: ActionType = Field(..., description="Category of anticipatory action")
    description: str = Field(..., description="Actionable instruction")
    deadline: str = Field(..., description="Execution deadline ISO timestamp")
    supporting_risk_ids: List[str] = Field(default_factory=list, description="Facility IDs justifying action")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Statistical confidence")


class AdvisoryValidation(BaseModel):
    passed: bool = Field(..., description="True if all numbers, times, and names exist in input JSON")
    checked_values: int = Field(..., description="Count of numerical and named entities validated")
    failures: List[str] = Field(default_factory=list, description="List of unverified tokens if any")


class StatusHistory(BaseModel):
    status: AdvisoryStatus = Field(...)
    at: str = Field(..., description="ISO timestamp")
    actor: str = Field(..., description="Operator or system identity")


class Advisory(BaseModel):
    id: str = Field(..., description="Advisory ID, e.g. adv-001")
    scenario_id: str = Field(..., description="Scenario ID")
    role: AdvisoryRole = Field(..., description="Target recipient role")
    language: str = Field(..., description="Language code: en, bn, hi, or")
    status: AdvisoryStatus = Field(default=AdvisoryStatus.DRAFT)
    text: str = Field(..., description="Validated advisory text content")
    plain_instruction: Optional[str] = Field(default=None, description="One-sentence plain-language citizen instruction")
    validation: AdvisoryValidation = Field(...)
    history: List[StatusHistory] = Field(default_factory=list)


class HazardLayerIndex(BaseModel):
    scenario_id: str = Field(...)
    time_step_h: int = Field(..., description="Hours relative to landfall (-24, -12, -6, 0, 6)")
    threshold_m: float = Field(..., description="Depth threshold in meters (e.g. 0.3, 1.0)")
    geojson: Dict[str, Any] = Field(..., description="FeatureCollection of probability contours")


class Scenario(BaseModel):
    id: str = Field(..., description="Unique scenario ID, e.g. amphan-2020-t-72h")
    name: str = Field(..., description="Human-readable scenario name")
    lead_time_h: int = Field(..., description="Forecast lead time in hours (e.g. 72)")
    forecast_time: str = Field(..., description="Timestamp of forecast issuance")
    ensemble_members: int = Field(default=40, description="Number of perturbed members")
    golden: bool = Field(default=False, description="True if frozen precomputed scenario")


class ParametricResult(BaseModel):
    district: str = Field(..., description="District name")
    trigger_probability: float = Field(..., ge=0.0, le=1.0, description="Probability trigger condition is met")
    payout_triggered: bool = Field(..., description="True if trigger probability >= policy threshold")
    payout_amount_usd: float = Field(default=0.0)
    basis_risk: str = Field(..., description="Assessment of false positive / false negative risk")


class CitizenStatusResponse(BaseModel):
    state: str = Field(..., description="Danger state: Safe, Watch, Warning, Danger")
    color: str = Field(..., description="Badge/theme color: green, yellow, orange, red")
    icon: str = Field(..., description="Icon identifier: check, eye, triangle, siren")
    headline: str = Field(..., description="Short single-glance headline")
    plain_message: str = Field(..., description="Plain-language status message")
    plain_instruction: str = Field(..., description="Plain-language citizen action instruction")
    district: str = Field(..., description="Selected or detected district")
    max_failure_probability: float = Field(..., description="Maximum facility failure probability in district")
    parametric_trigger_probability: float = Field(..., description="Parametric insurance trigger probability")
    has_evacuation_action: bool = Field(..., description="True if evacuation action is active for this district")
    shelter_info: Dict[str, Any] = Field(..., description="Nearest shelter details")
    emergency_contacts: List[Dict[str, str]] = Field(..., description="Key emergency phone numbers")
    actions: List[str] = Field(..., description="List of immediate citizen actions")
    advisory_id: Optional[str] = Field(default=None, description="Associated advisory ID if applicable")
    advisory_text: Optional[str] = Field(default=None, description="Full verified advisory text")
    last_updated: str = Field(..., description="ISO timestamp of last update")
    language: str = Field(..., description="Language code")

