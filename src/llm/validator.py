"""Aegis-APAC Advisory Guardrail & Fact Validator.

Hard Rule Enforcement:
Every number, timestamp, facility name, and road name in an advisory
must exist in the input decision JSON payload. Any discrepancy causes
immediate rejection and fallback to the deterministic safe template.
"""

import re
from typing import Any, Dict, List, Set, Tuple
from src.contracts import AdvisoryValidation


# Standard known emergency contact numbers and common units permitted in boilerplate
ALLOWED_BOILERPLATE_NUMBERS = {
    "1077", "112", "108", "100", "1", "2", "3", "4", "5", "24", "48", "72", "1070"
}


class AdvisoryValidator:
    """Enforces strict deterministic numerical and entity validation on all advisories."""

    def __init__(self, allowed_boilerplate: Set[str] = None):
        self.allowed_boilerplate = allowed_boilerplate or ALLOWED_BOILERPLATE_NUMBERS

    def extract_truth_tokens(self, decision_json: Dict[str, Any]) -> Tuple[Set[str], Set[str]]:
        """Extract all valid numbers, timestamps, and named entities from ground-truth input JSON."""
        numbers: Set[str] = set()
        entities: Set[str] = set()

        def recurse(data: Any):
            if isinstance(data, dict):
                for k, v in data.items():
                    if k in ("name", "id", "district", "ward") and isinstance(v, str):
                        entities.add(v.strip().lower())
                        # Also add individual significant words in name (e.g. "Ramnagar" from "Substation Ramnagar")
                        for part in v.replace("-", " ").replace("_", " ").split():
                            if len(part) > 2:
                                entities.add(part.strip().lower())
                    recurse(v)
            elif isinstance(data, list):
                for item in data:
                    recurse(item)
            elif isinstance(data, (int, float)):
                # Normalise numbers to string representations (e.g. 0.4, 0.40, 40%, 150)
                num_str = str(data)
                numbers.add(num_str)
                if isinstance(data, float):
                    numbers.add(f"{data:.1f}")
                    numbers.add(f"{data:.2f}")
                    numbers.add(f"{int(round(data * 100))}")  # e.g. 0.85 -> 85 (%)
                    numbers.add(f"{int(round(data))}")
            elif isinstance(data, str):
                # Search for numbers and ISO timestamps in strings
                found_nums = re.findall(r"\b\d+(?:\.\d+)?\b", data)
                for n in found_nums:
                    numbers.add(n)
                # Look for timestamps (e.g. 08:00, 2020-05-20)
                found_times = re.findall(r"\b\d{1,2}:\d{2}\b", data)
                for t in found_times:
                    numbers.add(t)

        recurse(decision_json)
        return numbers, entities

    @staticmethod
    def normalize_indic_digits(s: str) -> str:
        """Convert Bengali, Devanagari, and Odia numerals to standard ASCII digits."""
        res = []
        for ch in s:
            code = ord(ch)
            if 0x09E6 <= code <= 0x09EF:  # Bengali
                res.append(chr(ord('0') + (code - 0x09E6)))
            elif 0x0966 <= code <= 0x096F:  # Devanagari
                res.append(chr(ord('0') + (code - 0x0966)))
            elif 0x0B66 <= code <= 0x0B6F:  # Odia
                res.append(chr(ord('0') + (code - 0x0B66)))
            else:
                res.append(ch)
        return "".join(res)

    def validate(self, advisory_text: str, decision_json: Dict[str, Any]) -> AdvisoryValidation:
        """Validate all numbers and named entities in advisory_text against truth payload."""
        truth_numbers, truth_entities = self.extract_truth_tokens(decision_json)

        # Normalize Indic numerals so multilingual text is factually verified
        normalized_text = self.normalize_indic_digits(advisory_text)

        # Extract all numbers from advisory text (including percentages, depths, hours)
        text_numbers = re.findall(r"\b\d+(?:\.\d+)?\b", normalized_text)
        failures: List[str] = []
        checked_count = 0

        for num in text_numbers:
            checked_count += 1
            if num in self.allowed_boilerplate:
                continue

            # Check exact match or rounded match in truth numbers
            matched = False
            if num in truth_numbers:
                matched = True
            else:
                try:
                    val = float(num)
                    for tn in truth_numbers:
                        try:
                            if abs(float(tn) - val) < 1e-3:
                                matched = True
                                break
                        except ValueError:
                            pass
                except ValueError:
                    pass

            if not matched:
                failures.append(f"Ungrounded number: '{num}'")

        # Entity verification: look for mentions of facility names around infrastructure keywords
        ignore_words = {
            "has", "have", "is", "are", "was", "were", "will", "at", "to", "in", "on", "for",
            "with", "and", "or", "by", "before", "prior", "of", "from", "after", "near",
            "must", "should", "can", "may", "be", "been", "a", "an", "the", "this", "that",
            "failure", "inundation", "damage", "flooding", "risk", "status", "level",
            "ensure", "auxiliary", "emergency", "medical", "feeder", "feeders", "backup",
            "power", "switchgear", "islanding", "safe", "safety", "control", "room",
            "priority", "immediate", "all", "designated", "block", "officer", "officers"
        }

        # Check prefix: e.g. "Hospital Atlantis"
        after_matches = re.findall(r"(?:Substation|Hospital|Shelter|Highway|Road)\s+([A-Z][a-z0-9_-]+)", advisory_text)
        for ent in after_matches:
            ent_clean = ent.lower().strip()
            if ent_clean in ignore_words or re.match(r"^\d+[a-z]*$", ent_clean):
                continue
            checked_count += 1
            if ent_clean not in truth_entities:
                failures.append(f"Ungrounded facility name: '{ent}'")

        # Check suffix: e.g. "Atlantis Hospital"
        before_matches = re.findall(r"([A-Z][a-z0-9_-]+)\s+(?:Substation|Hospital|Shelter|Highway|Road)", advisory_text)
        for ent in before_matches:
            ent_clean = ent.lower().strip()
            if ent_clean in ignore_words or re.match(r"^\d+[a-z]*$", ent_clean):
                continue
            checked_count += 1
            if ent_clean not in truth_entities:
                failures.append(f"Ungrounded facility name: '{ent}'")

        passed = len(failures) == 0
        return AdvisoryValidation(
            passed=passed,
            checked_values=checked_count,
            failures=failures,
        )
