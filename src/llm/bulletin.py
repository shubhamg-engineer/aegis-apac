"""Aegis-APAC Storm Bulletin Parameter Extractor.

Parses unstructured meteorological bulletins (such as IMD Tropical Cyclone Advisories)
into structured physical cyclone parameters for initialization of the hazard model.
"""

import re
from typing import Any, Dict, Optional


class BulletinExtractor:
    """Extracts cyclone intensity, coordinates, and pressure from unstructured text bulletins."""

    def extract_parameters(self, bulletin_text: str) -> Dict[str, Any]:
        """Parse bulletin text using resilient regex pattern matching."""
        extracted: Dict[str, Any] = {
            "cyclone_name": "UNKNOWN",
            "central_pressure_hpa": 950.0,
            "max_sustained_wind_ms": 45.0,
            "radius_max_winds_km": 35.0,
            "center_lat": 21.5,
            "center_lon": 88.2,
            "movement_speed_kmh": 15.0,
            "stage": "Very Severe Cyclonic Storm",
        }

        # 1. Storm Name: handle quoted names 'AMPHAN' or CYCLONE <NAME> excluding bulletin keywords
        quoted_match = re.search(r"['\"]([A-Za-z]+)['\"]", bulletin_text)
        if quoted_match:
            extracted["cyclone_name"] = quoted_match.group(1).upper()
        else:
            name_match = re.search(
                r"(?:CYCLONIC\s+STORM|CYCLONE)\s+(?:SUPER\s+|SEVERE\s+)?['\"]?(?!ADVISORY|BULLETIN|WARNING|ALERT|OVER|NO|TRACK)([A-Z]{3,})['\"]?",
                bulletin_text,
                re.IGNORECASE,
            )
            if name_match:
                extracted["cyclone_name"] = name_match.group(1).upper()

        # 2. Coordinates: e.g. "LATITUDE 21.6 N AND LONGITUDE 88.3 E" or "21.6°N, 88.3°E"
        coord_match = re.search(r"(?:LAT|LATITUDE)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*°?\s*N.*?LONG(?:ITUDE)?\s*[:=]?\s*(\d+(?:\.\d+)?)\s*°?\s*E", bulletin_text, re.IGNORECASE)
        if coord_match:
            extracted["center_lat"] = float(coord_match.group(1))
            extracted["center_lon"] = float(coord_match.group(2))

        # 3. Central Pressure: e.g. "ESTIMATED CENTRAL PRESSURE 930 HPA"
        cp_match = re.search(r"(?:ESTIMATED\s+)?CENTRAL\s+PRESSURE\s*(?:IS\s+ABOUT)?\s*(\d{3,4})\s*(?:HPA|MB)", bulletin_text, re.IGNORECASE)
        if cp_match:
            extracted["central_pressure_hpa"] = float(cp_match.group(1))

        # 4. Maximum Sustained Surface Winds: e.g. "MAXIMUM SUSTAINED SURFACE WIND SPEED IS 85 KNOTS" or "155 KMPH"
        wind_kts_match = re.search(r"(\d{2,3})\s*(?:KNOTS|KTS)", bulletin_text, re.IGNORECASE)
        wind_kmph_match = re.search(r"(\d{2,3})\s*(?:KMPH|KM/H)", bulletin_text, re.IGNORECASE)
        if wind_kts_match:
            kts = float(wind_kts_match.group(1))
            extracted["max_sustained_wind_ms"] = round(kts * 0.514444, 1)
        elif wind_kmph_match:
            kmph = float(wind_kmph_match.group(1))
            extracted["max_sustained_wind_ms"] = round(kmph / 3.6, 1)

        # 5. Radius of Maximum Winds: e.g. "RADIUS OF MAXIMUM WINDS 30 KM"
        rmw_match = re.search(r"(?:RADIUS\s+OF\s+MAXIMUM\s+WIND|RMW)\s*(?:IS\s+ABOUT)?\s*(\d{1,3})\s*KM", bulletin_text, re.IGNORECASE)
        if rmw_match:
            extracted["radius_max_winds_km"] = float(rmw_match.group(1))

        # 6. Movement Speed: e.g. "MOVING NORTH-NORTHEASTWARDS WITH A SPEED OF 18 KMPH"
        mov_match = re.search(r"SPEED\s+OF\s+(\d{1,3})\s*(?:KMPH|KM/H)", bulletin_text, re.IGNORECASE)
        if mov_match:
            extracted["movement_speed_kmh"] = float(mov_match.group(1))

        return extracted
