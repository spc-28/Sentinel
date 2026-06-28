"""Optional GitHub integration: file the report as an issue, draft a revert PR.

Entirely optional — a no-op unless ``GITHUB_TOKEN`` is set and the service's repo
URL is parseable. Every call is best-effort: any API error is logged and skipped so
an investigation never fails because of GitHub. (Seeded repos are fake ``acme/*``,
so this stays a no-op until you point a service at a real repo you can write to.)
"""

from __future__ import annotations

import re

import httpx
import structlog
from packages.core.config import get_settings

log = structlog.get_logger()

_GITHUB_API = "https://api.github.com"
_REPO_RE = re.compile(r"github\.com[/:]([^/]+/[^/.]+)")


def parse_repo(repo_url: str | None) -> str | None:
    """Extract ``owner/repo`` from a GitHub URL."""
    if not repo_url:
        return None
    match = _REPO_RE.search(repo_url)
    return match.group(1) if match else None


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


async def create_issue(repo: str, title: str, body: str, token: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{_GITHUB_API}/repos/{repo}/issues",
                headers=_headers(token),
                json={"title": title, "body": body},
            )
            resp.raise_for_status()
            return str(resp.json()["html_url"])
    except Exception as exc:  # noqa: BLE001 - optional integration
        log.warning("github.issue_failed", repo=repo, error=str(exc))
        return None


async def create_draft_pr(
    repo: str, title: str, body: str, head: str, base: str, token: str
) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{_GITHUB_API}/repos/{repo}/pulls",
                headers=_headers(token),
                json={"title": title, "body": body, "head": head, "base": base, "draft": True},
            )
            resp.raise_for_status()
            return str(resp.json()["html_url"])
    except Exception as exc:  # noqa: BLE001 - branch/repo may not exist
        log.warning("github.draft_pr_failed", repo=repo, head=head, error=str(exc))
        return None


async def report_to_github(
    *,
    repo_url: str | None,
    title: str,
    body: str,
    revert_head: str | None = None,
    base_branch: str = "main",
) -> dict[str, str | None]:
    """Create an issue for the report and, if a revert branch is known, a draft PR."""
    token = get_settings().github_token
    repo = parse_repo(repo_url)
    if not token or repo is None:
        log.info("github.skipped", reason="no token" if not token else "no repo", repo=repo)
        return {"issue_url": None, "pr_url": None}

    issue_url = await create_issue(repo, title, body, token)
    pr_url = None
    if revert_head:
        pr_url = await create_draft_pr(
            repo, f"Revert: {title}", body, revert_head, base_branch, token
        )
    log.info("github.reported", repo=repo, issue=issue_url, pr=pr_url)
    return {"issue_url": issue_url, "pr_url": pr_url}
