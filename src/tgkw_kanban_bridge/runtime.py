from __future__ import annotations

import re
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .bridge import BridgeConfig

_SOURCE_ISSUE_URL_RE = re.compile(r"https://github\.com/[^\s/]+/[^\s/]+/issues/(\d+)")
_ISSUE_NUMBER_RE = re.compile(r"(?:^|\n)Issue:\s*#(\d+)")


@dataclass(frozen=True)
class KanbanStatusSummary:
    task_id: str
    title: str
    board: str
    status: str
    assignee: str
    tenant: str
    idempotency_key: str
    source_issue_url: str
    source_issue_number: int
    run_count: int
    latest_run_summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KanbanStatusSummary":
        return cls(
            task_id=str(data["task_id"]),
            title=str(data.get("title", "")),
            board=str(data["board"]),
            status=str(data["status"]),
            assignee=str(data.get("assignee", "")),
            tenant=str(data.get("tenant", "")),
            idempotency_key=str(data["idempotency_key"]),
            source_issue_url=str(data["source_issue_url"]),
            source_issue_number=int(data["source_issue_number"]),
            run_count=int(data.get("run_count", 0)),
            latest_run_summary=str(data.get("latest_run_summary", "")),
        )


def _task_from_show(show: dict[str, Any]) -> dict[str, Any]:
    task = show.get("task")
    if not isinstance(task, dict):
        raise ValueError("Kanban show JSON must contain a task object")
    return task


def _extract_source_issue_number(body: str) -> int:
    url_match = _SOURCE_ISSUE_URL_RE.search(body)
    if url_match:
        return int(url_match.group(1))
    issue_match = _ISSUE_NUMBER_RE.search(body)
    if issue_match:
        return int(issue_match.group(1))
    raise ValueError("Cannot infer GitHub issue number from Kanban task body")


def _extract_source_issue_url(body: str, issue_number: int, config: BridgeConfig) -> str:
    url_match = _SOURCE_ISSUE_URL_RE.search(body)
    if url_match:
        return url_match.group(0)
    return config.github.issue_url_template.format(number=issue_number)


def _latest_run_summary(show: dict[str, Any], runs: list[dict[str, Any]]) -> str:
    if runs:
        latest = runs[-1]
        for key in ("summary", "result", "outcome", "status"):
            value = latest.get(key)
            if value:
                return str(value)
    latest_summary = show.get("latest_summary")
    if latest_summary:
        return str(latest_summary)
    task = _task_from_show(show)
    result = task.get("result")
    return str(result or "")


def summarize_kanban_task(
    show: dict[str, Any],
    runs: list[dict[str, Any]],
    board: str,
    config: BridgeConfig,
) -> KanbanStatusSummary:
    task = _task_from_show(show)
    body = str(task.get("body") or "")
    source_issue_number = _extract_source_issue_number(body)
    source_issue_url = _extract_source_issue_url(body, source_issue_number, config)
    idempotency_key = config.defaults.idempotency_key_template.format(
        issue_number=source_issue_number,
        repo=config.github.repo,
    )

    return KanbanStatusSummary(
        task_id=str(task["id"]),
        title=str(task.get("title", "")),
        board=board,
        status=str(task.get("status", "")),
        assignee=str(task.get("assignee", "")),
        tenant=str(task.get("tenant", "")),
        idempotency_key=idempotency_key,
        source_issue_url=source_issue_url,
        source_issue_number=source_issue_number,
        run_count=len(runs),
        latest_run_summary=_latest_run_summary(show, runs),
    )


def render_github_audit_comment(summary: KanbanStatusSummary, header: str) -> str:
    latest_run = summary.latest_run_summary or "(no run summary yet)"
    return "\n".join(
        [
            header,
            "",
            "## Hermes Kanban 运行态回写",
            "",
            "### Runtime snapshot",
            "",
            f"- task id：`{summary.task_id}`",
            f"- board：`{summary.board}`",
            f"- status：`{summary.status}`",
            f"- assignee：`{summary.assignee}`",
            f"- tenant：`{summary.tenant}`",
            f"- idempotency-key：`{summary.idempotency_key}`",
            f"- source issue：{summary.source_issue_url}",
            f"- run count：`{summary.run_count}`",
            f"- latest run：{latest_run}",
            "",
            "### Boundary",
            "",
            "- 本回写来自 Hermes Kanban 公开 CLI 输出。",
            "- 不直接写 `kanban.db`。",
            "- 不依赖 Hermes 内部 Python API。",
            "- GitHub 访问应继续走代理隔离后的 gh wrapper。",
            "",
        ]
    )


def render_github_comment_command(
    config: BridgeConfig,
    issue_number: int,
    body_file: str | Path,
) -> str:
    return " ".join(
        [
            config.github.gh_command,
            "issue",
            "comment",
            shlex.quote(str(issue_number)),
            "--repo",
            shlex.quote(config.github.repo),
            "--body-file",
            shlex.quote(str(body_file)),
        ]
    )
