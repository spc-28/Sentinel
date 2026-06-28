"""Convert Grafana and Datadog alert webhooks into Sentinel's AlertWebhook shape."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from packages.core.enums import AlertSeverity
from packages.core.schemas import AlertWebhook

# Grafana `severity` label / Datadog alert_type → our severity.
_GRAFANA_SEVERITY = {
    "critical": AlertSeverity.critical,
    "high": AlertSeverity.high,
    "error": AlertSeverity.high,
    "warning": AlertSeverity.medium,
    "info": AlertSeverity.low,
}
_DATADOG_SEVERITY = {
    "error": AlertSeverity.high,
    "warning": AlertSeverity.medium,
    "info": AlertSeverity.low,
    "success": AlertSeverity.info,
}
_DATADOG_PRIORITY = {
    "p1": AlertSeverity.critical,
    "p2": AlertSeverity.high,
    "p3": AlertSeverity.medium,
    "p4": AlertSeverity.low,
}


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def grafana_to_alerts(payload: dict[str, Any]) -> list[AlertWebhook]:
    """Grafana (v9+) alerting webhook → one AlertWebhook per firing alert."""
    alerts: list[AlertWebhook] = []
    for item in payload.get("alerts", []):
        if item.get("status") not in (None, "firing"):
            continue
        labels = item.get("labels", {})
        annotations = item.get("annotations", {})
        severity = _GRAFANA_SEVERITY.get(
            str(labels.get("severity", "")).lower(), AlertSeverity.medium
        )
        title = labels.get("alertname") or annotations.get("summary") or "Grafana alert"
        alerts.append(
            AlertWebhook(
                service=labels.get("service") or labels.get("job"),
                title=title,
                severity=severity,
                source="grafana",
                fingerprint=item.get("fingerprint"),
                triggered_at=_parse_ts(item.get("startsAt")),
                payload={"labels": labels, "annotations": annotations},
            )
        )
    return alerts


def _service_from_tags(tags: Any) -> str | None:
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, str) and tag.startswith("service:"):
                return tag.split(":", 1)[1]
    return None


def datadog_to_alert(payload: dict[str, Any]) -> AlertWebhook:
    """Datadog monitor webhook → one AlertWebhook."""
    priority = str(payload.get("priority", "")).lower()
    alert_type = str(payload.get("alert_type", "")).lower()
    severity = _DATADOG_PRIORITY.get(priority) or _DATADOG_SEVERITY.get(
        alert_type, AlertSeverity.medium
    )
    return AlertWebhook(
        service=_service_from_tags(payload.get("tags")),
        title=payload.get("title") or "Datadog alert",
        severity=severity,
        source="datadog",
        fingerprint=str(payload["id"]) if payload.get("id") is not None else None,
        triggered_at=_parse_ts(payload.get("date") or payload.get("last_updated")),
        payload={"body": payload.get("body"), "tags": payload.get("tags")},
    )
