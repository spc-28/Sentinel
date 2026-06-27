"""Incident fingerprints and signatures for memory matching.

A *fingerprint* is a stable short hash of the structural identity of an incident
(service + alert type + main error), used for exact-match recall. A *signature*
carries the same parts plus a natural-language ``text`` for meaning-based
similarity.

Both are derived from the *alert alone* (never from gathered evidence), so the
fingerprint is identical whether it is computed cheaply at recall time (before any
investigation) or later when the incident is saved. That is what lets the second
occurrence of a problem match the first.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from pydantic import BaseModel

_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_HEX = re.compile(r"\b(?:0x)?[0-9a-f]{6,}\b")
_DIGITS = re.compile(r"\d+")
_WS = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Canonicalise a message so variable parts (ids, counts, timings) don't
    fragment otherwise-identical incidents ("timeout after 5123ms" == "... 87ms")."""
    lowered = text.lower().strip()
    lowered = _UUID.sub("<id>", lowered)
    lowered = _HEX.sub("<hex>", lowered)
    lowered = _DIGITS.sub("<n>", lowered)
    return _WS.sub(" ", lowered).strip()


class IncidentSignature(BaseModel):
    service: str
    alert_type: str
    main_error: str
    text: str  # natural-language signature for embedding / lexical match


def _main_error(alert: dict[str, Any]) -> str:
    details = alert.get("details")
    if isinstance(details, dict):
        for key in ("error", "message", "main_error", "reason"):
            value = details.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return str(alert.get("title", "")).strip()


def signature_from_alert(alert: dict[str, Any]) -> IncidentSignature:
    """Derive an incident signature from the alert payload."""
    service = str(alert.get("service", "unknown")) or "unknown"
    alert_type = str(alert.get("title", "")).strip() or "unknown"
    main_error = _main_error(alert) or alert_type
    text = f"{service}: {alert_type} — {main_error}".strip()
    return IncidentSignature(
        service=service, alert_type=alert_type, main_error=main_error, text=text
    )


def fingerprint(signature: IncidentSignature) -> str:
    """A stable 16-char hash of the normalised (service, alert type, main error)."""
    joined = "|".join(
        normalize(part) for part in (signature.service, signature.alert_type, signature.main_error)
    )
    return hashlib.sha1(joined.encode(), usedforsecurity=False).hexdigest()[:16]
