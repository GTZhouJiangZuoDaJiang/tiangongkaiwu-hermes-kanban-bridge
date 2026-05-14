from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class BoardConfig:
    slug: str
    name: str


@dataclass(frozen=True)
class GithubConfig:
    repo: str
    issue_url_template: str
    gh_command: str


@dataclass(frozen=True)
class DefaultsConfig:
    workspace: str
    tenant: str
    idempotency_key_template: str
    skills: tuple[str, ...]


@dataclass(frozen=True)
class BridgeConfig:
    board: BoardConfig
    github: GithubConfig
    defaults: DefaultsConfig
    profiles: dict[str, str]
    states: dict[str, Any]


@dataclass(frozen=True)
class KanbanPlan:
    title: str
    board: str
    assignee: str
    tenant: str
    workspace: str
    idempotency_key: str
    body: str
    skills: tuple[str, ...]
    source_issue_url: str
    source_repo: str
    source_issue_number: int
    triage: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _require(mapping: dict[str, Any], key: str, path: str) -> Any:
    if key not in mapping or mapping[key] in (None, ""):
        raise ValueError(f"Missing required config key: {path}.{key}")
    return mapping[key]


def load_config(path: str | Path) -> BridgeConfig:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Config must be a mapping: {config_path}")

    board_raw = _require(raw, "board", "root")
    github_raw = _require(raw, "github", "root")
    defaults_raw = _require(raw, "defaults", "root")
    profiles = dict(_require(raw, "profiles", "root"))

    return BridgeConfig(
        board=BoardConfig(
            slug=str(_require(board_raw, "slug", "board")),
            name=str(_require(board_raw, "name", "board")),
        ),
        github=GithubConfig(
            repo=str(_require(github_raw, "repo", "github")),
            issue_url_template=str(_require(github_raw, "issue_url_template", "github")),
            gh_command=str(_require(github_raw, "gh_command", "github")),
        ),
        defaults=DefaultsConfig(
            workspace=str(_require(defaults_raw, "workspace", "defaults")),
            tenant=str(_require(defaults_raw, "tenant", "defaults")),
            idempotency_key_template=str(
                _require(defaults_raw, "idempotency_key_template", "defaults")
            ),
            skills=tuple(str(skill) for skill in defaults_raw.get("skills", [])),
        ),
        profiles={str(role): str(profile) for role, profile in profiles.items()},
        states=dict(raw.get("states", {})),
    )


def _issue_number(issue: dict[str, Any]) -> int:
    try:
        return int(issue["number"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Issue JSON must contain an integer-compatible 'number'") from exc


def _issue_url(issue: dict[str, Any], config: BridgeConfig) -> str:
    number = _issue_number(issue)
    return str(
        issue.get("html_url")
        or issue.get("url")
        or config.github.issue_url_template.format(number=number)
    )


def _issue_body(issue: dict[str, Any]) -> str:
    body = issue.get("body") or ""
    if not isinstance(body, str):
        raise ValueError("Issue JSON 'body' must be a string when present")
    return body.strip()


def render_task_body(issue: dict[str, Any], config: BridgeConfig) -> str:
    number = _issue_number(issue)
    url = _issue_url(issue, config)
    source_body = _issue_body(issue)
    title = str(issue.get("title") or f"GitHub issue #{number}")

    return "\n".join(
        [
            f"GitHub: {url}",
            f"Repo: {config.github.repo}",
            f"Issue: #{number}",
            "",
            "Summary:",
            title,
            "",
            "Acceptance:",
            source_body or "(No issue body provided.)",
        ]
    )


def build_plan(
    issue: dict[str, Any],
    config: BridgeConfig,
    assignee_role: str,
    triage: bool = False,
) -> KanbanPlan:
    if assignee_role not in config.profiles:
        known = ", ".join(sorted(config.profiles))
        raise ValueError(f"Unknown assignee role '{assignee_role}'. Known roles: {known}")

    number = _issue_number(issue)
    title = str(issue.get("title") or f"GitHub issue #{number}")
    return KanbanPlan(
        title=title,
        board=config.board.slug,
        assignee=config.profiles[assignee_role],
        tenant=config.defaults.tenant,
        workspace=config.defaults.workspace,
        idempotency_key=config.defaults.idempotency_key_template.format(
            issue_number=number,
            repo=config.github.repo,
        ),
        body=render_task_body(issue, config),
        skills=config.defaults.skills,
        source_issue_url=_issue_url(issue, config),
        source_repo=config.github.repo,
        source_issue_number=number,
        triage=triage,
    )


def render_kanban_command(plan: KanbanPlan) -> list[str]:
    command = [
        "hermes",
        "kanban",
        "--board",
        plan.board,
        "create",
        plan.title,
        "--assignee",
        plan.assignee,
        "--tenant",
        plan.tenant,
        "--workspace",
        plan.workspace,
        "--idempotency-key",
        plan.idempotency_key,
    ]
    for skill in plan.skills:
        command.extend(["--skill", skill])
    if plan.triage:
        command.append("--triage")
    command.extend(["--body", plan.body, "--json"])
    return command
