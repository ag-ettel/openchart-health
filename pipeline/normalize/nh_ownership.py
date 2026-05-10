"""
Normalizer for Nursing Home Ownership dataset (y2hd-n93e).

One row per owner/entity per facility. Output → provider_ownership table.
Phase 0 reference: docs/phase_0_findings.md §20
"""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)

DATASET_ID = "y2hd-n93e"


def _parse_association_date(raw: str | None) -> date | None:
    """Parse 'since MM/DD/YYYY' format to date."""
    if not raw or not raw.strip():
        return None
    cleaned = raw.strip()
    # Strip "since " prefix if present
    if cleaned.lower().startswith("since "):
        cleaned = cleaned[6:].strip()
    # Try MM/DD/YYYY
    match = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", cleaned)
    if match:
        try:
            return date(int(match.group(3)), int(match.group(1)), int(match.group(2)))
        except ValueError:
            pass
    logger.warning("Unparseable association_date: %r", raw)
    return None


def _parse_ownership_percentage(raw: str | None) -> tuple[int | None, bool]:
    """Parse ownership percentage. Returns (percentage, not_provided).

    "5%" → (5, False)
    "100%" → (100, False)
    "NOT APPLICABLE" → (None, False)
    "NO PERCENTAGE PROVIDED" → (None, True)
    "" → (None, False)
    """
    if not raw or not raw.strip():
        return None, False
    cleaned = raw.strip().upper()
    if cleaned == "NO PERCENTAGE PROVIDED":
        return None, True
    if cleaned == "NOT APPLICABLE":
        return None, False
    # Try to parse "5%", "100%", or bare numbers
    match = re.match(r"^(\d+)%?$", cleaned)
    if match:
        return int(match.group(1)), False
    logger.warning("Unparseable ownership_percentage: %r", raw)
    return None, False


def normalize_row(raw: dict[str, str]) -> dict[str, Any] | None:
    provider_id = raw.get("facility_id", "").strip().zfill(6)
    if not provider_id or provider_id == "000000":
        return None

    owner_name = raw.get("owner_name", "").strip()
    if not owner_name:
        return None

    pct, not_provided = _parse_ownership_percentage(raw.get("ownership_percentage"))

    return {
        "provider_id": provider_id,
        "provider_type": "NURSING_HOME",
        "owner_name": owner_name,
        "owner_type": raw.get("owner_type", "").strip() or "Unknown",
        "role": raw.get("role_played_by_owner_or_manager_in_facility", "").strip() or "Unknown",
        "ownership_percentage": pct,
        "ownership_percentage_raw": raw.get("ownership_percentage", "").strip(),
        "ownership_percentage_not_provided": not_provided,
        "association_date": _parse_association_date(raw.get("association_date")),
        "association_date_raw": raw.get("association_date", "").strip(),
        "source_dataset_id": DATASET_ID,
    }


def normalize_dataset(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [r for r in (normalize_row(raw) for raw in rows) if r is not None]
