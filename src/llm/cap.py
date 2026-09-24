"""Aegis-APAC OASIS Common Alerting Protocol (CAP 1.2) Exporter.

Converts validated, human-approved early-warning advisories into standard
CAP 1.2 XML for interoperable broadcast to NDMA, civil protection, and CAP aggregators.
"""

from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from src.contracts import Advisory


class CAPExporter:
    """Serializes Advisory contracts to standard OASIS CAP 1.2 XML documents."""

    @staticmethod
    def to_cap_xml(advisory: Advisory, sender: str = "operations@aegis-apac.org") -> str:
        """Convert Advisory to a full CAP 1.2 XML string."""
        alert = ET.Element("alert", xmlns="urn:oasis:names:tc:emergency:cap:1.2")
        ET.SubElement(alert, "identifier").text = f"AEGIS-APAC-{advisory.id}"
        ET.SubElement(alert, "sender").text = sender
        ET.SubElement(alert, "sent").text = datetime.now(timezone.utc).isoformat()
        ET.SubElement(alert, "status").text = "Actual" if advisory.status.value in ("approved", "dispatched") else "Draft"
        ET.SubElement(alert, "msgType").text = "Alert"
        ET.SubElement(alert, "scope").text = "Public"

        info = ET.SubElement(alert, "info")
        ET.SubElement(info, "language").text = advisory.language
        ET.SubElement(info, "category").text = "Met"
        ET.SubElement(info, "event").text = "Tropical Cyclone Coastal Impact"
        ET.SubElement(info, "urgency").text = "Expected"
        ET.SubElement(info, "severity").text = "Severe"
        ET.SubElement(info, "certainty").text = "Likely"
        ET.SubElement(info, "headline").text = f"Anticipatory Warning - Role: {advisory.role.value}"
        ET.SubElement(info, "description").text = advisory.text

        return ET.tostring(alert, encoding="utf-8", xml_declaration=True).decode("utf-8")
