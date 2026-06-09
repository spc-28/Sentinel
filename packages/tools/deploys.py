"""Deploy tools — recent deploys, their file changes, and a revert *suggestion*.

Uses the real GitHub API when ``GITHUB_TOKEN`` is set, otherwise deterministic
fake data. ``draft_revert`` only builds a suggested PR link; it never reverts.

Deploy ids have the form ``"<service>:<sha12>"`` so changes/reverts can be derived
without extra lookups.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import httpx
import structlog
from pydantic import BaseModel

from packages.core.config import get_settings
from packages.tools.common import now, rng

log = structlog.get_logger()

_GITHUB_API = "https://api.github.com"
_AUTHORS = ("alice", "bob", "carol", "dave", "erin")
_MESSAGES = (
    "fix: handle null customer id",
    "feat: add retry to payment client",
    "refactor: extract validation helper",
    "perf: cache service lookups",
    "chore: bump dependencies",
    "fix: correct timezone handling",
)
_FILE_TEMPLATES = (
    "src/{svc}/handlers.py",
    "src/{svc}/models.py",
    "src/{svc}/client.py",
    "tests/test_{svc}.py",
    "config/settings.yaml",
    "README.md",
)


class FileChange(BaseModel):
    filename: str
    status: str  # added | modified | removed
    additions: int
    deletions: int


class Deploy(BaseModel):
    deploy_id: str
    service: str
    sha: str
    author: str
    message: str
    timestamp: datetime
    status: str  # success | failed | rolled_back
    source: str  # github | fake


class DeployChanges(BaseModel):
    deploy_id: str
    sha: str
    files: list[FileChange]
    total_additions: int
    total_deletions: int


class RevertDraft(BaseModel):
    deploy_id: str
    service: str
    sha: str
    title: str
    body: str
    revert_pr_url: str
    note: str


def _repo(service: str) -> str:
    return f"acme/{service}"


def _deploy_id(service: str, sha: str) -> str:
    return f"{service}:{sha[:12]}"


def _split_deploy_id(deploy_id: str) -> tuple[str, str]:
    service, _, sha = deploy_id.rpartition(":")
    return service, sha


# --- GitHub (optional) ---------------------------------------------------
def _github_client(token: str) -> httpx.Client:
    return httpx.Client(
        base_url=_GITHUB_API,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        timeout=5.0,
    )


def _github_deploys(service: str, token: str, last_n_minutes: int) -> list[Deploy]:
    since = (now() - timedelta(minutes=last_n_minutes)).isoformat()
    with _github_client(token) as client:
        resp = client.get(f"/repos/{_repo(service)}/commits", params={"since": since})
        resp.raise_for_status()
        commits = resp.json()
    deploys: list[Deploy] = []
    for c in commits:
        sha = c["sha"]
        commit = c["commit"]
        deploys.append(
            Deploy(
                deploy_id=_deploy_id(service, sha),
                service=service,
                sha=sha,
                author=commit["author"]["name"],
                message=commit["message"].splitlines()[0],
                timestamp=datetime.fromisoformat(commit["author"]["date"].replace("Z", "+00:00")),
                status="success",
                source="github",
            )
        )
    return deploys


# --- Fake ----------------------------------------------------------------
def _fake_deploys(service: str, last_n_minutes: int) -> list[Deploy]:
    r = rng("deploys", service, last_n_minutes)
    count = r.randint(1, 5)
    deploys: list[Deploy] = []
    for _ in range(count):
        sha = f"{r.getrandbits(160):040x}"
        status = r.choices(("success", "failed", "rolled_back"), weights=(0.8, 0.1, 0.1))[0]
        deploys.append(
            Deploy(
                deploy_id=_deploy_id(service, sha),
                service=service,
                sha=sha,
                author=r.choice(_AUTHORS),
                message=r.choice(_MESSAGES),
                timestamp=now() - timedelta(minutes=r.randint(0, last_n_minutes)),
                status=status,
                source="fake",
            )
        )
    deploys.sort(key=lambda d: d.timestamp, reverse=True)
    return deploys


def recent_deploys(service: str, last_n_minutes: int = 1440) -> list[Deploy]:
    """Deploys for ``service`` in the window (GitHub if a token is set, else fake)."""
    token = get_settings().github_token
    if token:
        try:
            return _github_deploys(service, token, last_n_minutes)
        except Exception as exc:  # noqa: BLE001 - fall back to fake on any GitHub error
            log.warning("deploys.github_failed", service=service, error=str(exc))
    return _fake_deploys(service, last_n_minutes)


def get_deploy_changes(deploy_id: str) -> DeployChanges:
    """Files changed in a deploy (fake data keyed off the deploy id)."""
    service, sha = _split_deploy_id(deploy_id)
    r = rng("deploy-changes", deploy_id)
    chosen = r.sample(_FILE_TEMPLATES, k=r.randint(1, len(_FILE_TEMPLATES)))
    files = [
        FileChange(
            filename=tpl.format(svc=service.replace("-", "_")),
            status=r.choices(("modified", "added", "removed"), weights=(0.7, 0.2, 0.1))[0],
            additions=r.randint(0, 120),
            deletions=r.randint(0, 60),
        )
        for tpl in chosen
    ]
    return DeployChanges(
        deploy_id=deploy_id,
        sha=sha,
        files=files,
        total_additions=sum(f.additions for f in files),
        total_deletions=sum(f.deletions for f in files),
    )


def draft_revert(deploy_id: str) -> RevertDraft:
    """Prepare a revert PR suggestion for a deploy. Does not actually revert."""
    service, sha = _split_deploy_id(deploy_id)
    return RevertDraft(
        deploy_id=deploy_id,
        service=service,
        sha=sha,
        title=f"Revert deploy {sha} on {service}",
        body=(
            f"This is an automated **suggestion** to revert commit `{sha}` in "
            f"`{_repo(service)}`. Review the diff before merging."
        ),
        revert_pr_url=f"https://github.com/{_repo(service)}/compare/revert-{sha}?expand=1",
        note="Suggestion only — no revert was performed.",
    )
