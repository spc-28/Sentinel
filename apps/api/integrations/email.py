"""Email investigation reports via Gmail SMTP.

Sends only when SMTP user + app password + recipient are configured; otherwise the
rendered report is logged (so the flow works with no credentials). Blocking SMTP I/O
runs in a thread to keep the worker's event loop free.
"""

from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog
from packages.core.config import get_settings

log = structlog.get_logger()


def _render(
    *,
    service: str,
    alert_title: str,
    root_cause: str,
    recommended_fix: str | None,
    evidence: list[str],
    link: str,
) -> tuple[str, str, str]:
    """Return (subject, text_body, html_body)."""
    subject = f"[Sentinel] {service}: {root_cause[:80]}"
    fix = recommended_fix or "No fix suggested."
    evidence_lines = evidence or ["(no evidence captured)"]

    text = (
        f"Sentinel investigation report\n\n"
        f"What broke: {alert_title} ({service})\n\n"
        f"Likely cause:\n{root_cause}\n\n"
        f"Evidence:\n" + "\n".join(f"- {e}" for e in evidence_lines) + "\n\n"
        f"Suggested fix:\n{fix}\n\n"
        f"Full report: {link}\n"
    )

    evidence_html = "".join(f"<li>{e}</li>" for e in evidence_lines)
    html = f"""\
<html><body style="font-family: -apple-system, Segoe UI, Roboto, sans-serif; color:#1a1a1a;">
  <h2 style="margin-bottom:4px;">🛡️ Sentinel investigation report</h2>
  <p style="color:#666;margin-top:0;">What broke: <b>{alert_title}</b> on <b>{service}</b></p>
  <h3>Likely cause</h3>
  <p>{root_cause}</p>
  <h3>Evidence</h3>
  <ul>{evidence_html}</ul>
  <h3>Suggested fix</h3>
  <p>{fix}</p>
  <p><a href="{link}" style="background:#2563eb;color:#fff;padding:8px 14px;border-radius:6px;
     text-decoration:none;">View full report</a></p>
</body></html>"""
    return subject, text, html


def _send_sync(subject: str, text: str, html: str, sender: str) -> None:
    settings = get_settings()
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = settings.email_to or ""
    message.attach(MIMEText(text, "plain"))
    message.attach(MIMEText(html, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls(context=ssl.create_default_context())
        server.login(settings.smtp_user or "", settings.smtp_password or "")
        server.send_message(message)


async def send_investigation_report(
    *,
    investigation_id: str,
    service: str,
    alert_title: str,
    root_cause: str,
    recommended_fix: str | None,
    evidence: list[str],
) -> None:
    """Email the finished report (or log it if email isn't configured)."""
    settings = get_settings()
    link = f"{settings.report_link_base}/{investigation_id}"
    subject, text, html = _render(
        service=service,
        alert_title=alert_title,
        root_cause=root_cause,
        recommended_fix=recommended_fix,
        evidence=evidence,
        link=link,
    )

    if not settings.email_enabled:
        log.info("email.skipped_logging_only", subject=subject, to=settings.email_to, body=text)
        return

    sender = settings.email_from or settings.smtp_user or ""
    try:
        await asyncio.to_thread(_send_sync, subject, text, html, sender)
        log.info("email.sent", to=settings.email_to, subject=subject)
    except Exception as exc:  # noqa: BLE001 - never fail an investigation over email
        log.error("email.send_failed", error=str(exc))
