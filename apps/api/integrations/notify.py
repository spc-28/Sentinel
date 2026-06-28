"""Fan out a finished investigation to email + GitHub (both optional/graceful)."""

from __future__ import annotations

from uuid import UUID

import structlog
from packages.agents.state import ReportDoc

from apps.api.integrations.email import send_investigation_report
from apps.api.integrations.github import report_to_github

log = structlog.get_logger()


async def notify_investigation_complete(
    *,
    investigation_id: UUID,
    service: str,
    alert_title: str,
    report: ReportDoc,
    repo_url: str | None,
) -> None:
    """Email the report and file it as a GitHub issue (+ draft revert PR if applicable)."""
    evidence = list(report.evidence)[:8]
    await send_investigation_report(
        investigation_id=str(investigation_id),
        service=service,
        alert_title=alert_title,
        root_cause=report.root_cause,
        recommended_fix=report.suggested_fix,
        evidence=evidence,
    )

    revert_head = None
    if report.suggested_fix:
        try:
            from packages.tools.deploys import recent_deploys

            deploys = recent_deploys(service, 1440)
            if deploys:
                revert_head = f"revert-{deploys[0].sha[:12]}"
        except Exception as exc:  # noqa: BLE001 - deploys optional
            log.warning("notify.revert_head_failed", error=str(exc))

    await report_to_github(
        repo_url=repo_url,
        title=f"[Sentinel] {service}: {report.root_cause[:80]}",
        body=report.markdown,
        revert_head=revert_head,
    )
