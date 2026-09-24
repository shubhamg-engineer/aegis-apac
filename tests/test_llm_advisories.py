"""Unit and adversarial tests for Phase 7 Gemini Multimodal Layer and Guardrails.

Verifies:
1. Strict factual validation rejects hallucinated numbers and ungrounded entities.
2. Deterministic templates render across 4 languages and pass validation.
3. Fallback mechanism engages when LLM fails or generates invalid tokens.
4. Bulletin extractor reliably parses storm parameters.
5. Visual QA reviewer flags planted inconsistencies without overriding ground-truth.
6. CAP 1.2 XML serializer produces compliant alert documents.
"""

from typing import Any, Dict
import pytest

from src.contracts import AdvisoryRole, AdvisoryStatus, Facility, FacilityType, RiskResult
from src.llm.bulletin import BulletinExtractor
from src.llm.cap import CAPExporter
from src.llm.generator import AdvisoryGenerator
from src.llm.qa_reviewer import VisualQAReviewer
from src.llm.templates import DeterministicTemplateEngine
from src.llm.validator import AdvisoryValidator


@pytest.fixture
def sample_decision_payload() -> Dict[str, Any]:
    return {
        "scenario": {
            "name": "Cyclone Amphan",
            "lead_time_h": 72,
            "forecast_time": "2020-05-17T12:00:00Z",
        },
        "facilities": [
            {
                "id": "sub_digha",
                "name": "Digha Coastal Substation",
                "type": "substation",
            },
            {
                "id": "hosp_contai",
                "name": "Contai Sub-Divisional Hospital",
                "type": "hospital",
            }
        ],
        "risks": [
            {
                "facility_id": "sub_digha",
                "failure_probability": 0.85,
                "hours_of_warning": 18.0,
                "earliest_failure_time": "2020-05-20T06:00:00Z",
                "cause_chain": [],
            }
        ],
        "actions": [
            {
                "id": "act-001",
                "type": "deenergise",
                "description": "Controlled de-energisation of Digha Coastal Substation 2h prior to inundation.",
                "deadline": "2020-05-20T04:00:00Z",
            }
        ]
    }


def test_validator_accepts_grounded_text(sample_decision_payload):
    validator = AdvisoryValidator()
    valid_text = (
        "Cyclone Amphan (T-72h): Digha Coastal Substation has an 85% probability of failure with 18 hours of warning. "
        "Controlled de-energisation of Digha Coastal Substation 2h prior to inundation. Call 1077 for emergency."
    )
    res = validator.validate(valid_text, sample_decision_payload)
    assert res.passed is True
    assert len(res.failures) == 0


def test_validator_rejects_hallucinated_numbers(sample_decision_payload):
    validator = AdvisoryValidator()
    # Hallucinated number "99%" and "5.8m" not in input JSON
    hallucinated_text = (
        "Cyclone Amphan: Digha Coastal Substation has a 99% probability of failure with 5.8m flood depth."
    )
    res = validator.validate(hallucinated_text, sample_decision_payload)
    assert res.passed is False
    assert any("99" in f for f in res.failures) or any("5.8" in f for f in res.failures)


def test_validator_rejects_ungrounded_facility(sample_decision_payload):
    validator = AdvisoryValidator()
    ungrounded_text = "Hospital Atlantis will collapse within 18 hours."
    res = validator.validate(ungrounded_text, sample_decision_payload)
    assert res.passed is False
    assert any("Atlantis" in f for f in res.failures)


def test_deterministic_templates_pass_validation_across_all_languages(sample_decision_payload):
    validator = AdvisoryValidator()
    engine = DeterministicTemplateEngine()

    for role in [AdvisoryRole.COLLECTOR, AdvisoryRole.POWER_OPERATOR, AdvisoryRole.CITIZENS]:
        for lang in ["en", "bn", "hi", "or"]:
            text = engine.render(role, lang, sample_decision_payload)
            assert len(text) > 20
            # Must pass validator
            val = validator.validate(text, sample_decision_payload)
            assert val.passed is True, f"Template failed validation for role={role.value}, lang={lang}: {val.failures}"


def test_advisory_generator_caching_and_fallback(sample_decision_payload):
    generator = AdvisoryGenerator()  # No API key -> deterministic fallback mode
    adv1 = generator.generate(
        advisory_id="adv-test-01",
        scenario_id="amphan-2020",
        role=AdvisoryRole.COLLECTOR,
        language="en",
        decision_payload=sample_decision_payload,
    )

    assert adv1.validation.passed is True
    assert adv1.status == AdvisoryStatus.DRAFT
    assert "Digha Coastal Substation" in adv1.text

    # Second call should return cached instance
    adv2 = generator.generate(
        advisory_id="adv-test-01",
        scenario_id="amphan-2020",
        role=AdvisoryRole.COLLECTOR,
        language="en",
        decision_payload=sample_decision_payload,
    )
    assert adv1 is adv2


def test_bulletin_parameter_extractor():
    sample_bulletin = """
    INDIA METEOROLOGICAL DEPARTMENT
    TROPICAL CYCLONE ADVISORY NO. 15
    SUPER CYCLONIC STORM 'AMPHAN' OVER WESTCENTRAL BAY OF BENGAL.
    THE SUPER CYCLONIC STORM AMPHAN MOVED NORTH-NORTHEASTWARDS WITH A SPEED OF 15 KMPH.
    LATITUDE 21.65 N AND LONGITUDE 88.35 E.
    ESTIMATED CENTRAL PRESSURE IS ABOUT 930 HPA.
    MAXIMUM SUSTAINED SURFACE WIND SPEED IS 85 KNOTS GUSTING TO 95 KNOTS.
    RADIUS OF MAXIMUM WIND IS ABOUT 30 KM.
    """
    extractor = BulletinExtractor()
    params = extractor.extract_parameters(sample_bulletin)

    assert params["cyclone_name"] == "AMPHAN"
    assert params["center_lat"] == 21.65
    assert params["center_lon"] == 88.35
    assert params["central_pressure_hpa"] == 930.0
    assert 40.0 <= params["max_sustained_wind_ms"] <= 50.0  # ~43.7 m/s (85 kts)
    assert params["radius_max_winds_km"] == 30.0


def test_visual_qa_reviewer_flags_inconsistencies():
    reviewer = VisualQAReviewer()
    facilities = [
        Facility(id="fac1", type=FacilityType.HOSPITAL, name="Sagar Hospital", geometry={"type": "Point", "coordinates": [0, 0]}, elevation_m=1.0),
    ]
    # Planted inconsistency: 0.9m inundation depth but reported 0% failure probability!
    risks = [
        RiskResult(facility_id="fac1", scenario_id="sc1", failure_probability=0.0, earliest_failure_time="2020-05-20T00:00:00Z", hours_of_warning=12.0),
    ]
    depths = {"fac1": 0.9}

    flags = reviewer.review_consistency(facilities, risks, depths)
    assert len(flags) == 1
    assert flags[0]["facility_id"] == "fac1"
    assert flags[0]["severity"] == "HIGH"
    assert flags[0]["override_permitted"] is False


def test_cap_12_xml_export(sample_decision_payload):
    generator = AdvisoryGenerator()
    adv = generator.generate(
        advisory_id="adv-cap-01",
        scenario_id="amphan-2020",
        role=AdvisoryRole.CITIZENS,
        language="en",
        decision_payload=sample_decision_payload,
    )

    xml_output = CAPExporter.to_cap_xml(adv)
    assert 'xmlns="urn:oasis:names:tc:emergency:cap:1.2"' in xml_output
    assert "<identifier>AEGIS-APAC-adv-cap-01</identifier>" in xml_output
    assert "<headline>Anticipatory Warning - Role: citizens</headline>" in xml_output
