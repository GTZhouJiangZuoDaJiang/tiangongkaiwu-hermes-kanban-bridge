from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Sequence

from .bridge import load_config
from .runtime import summarize_dispatch_progress


DEFAULT_TARGET_STATUSES = ("ready", "running", "done", "blocked")


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _run_json_command(command: list[str]) -> Any:
    result = subprocess.run(
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return json.loads(result.stdout)


def _run_text_command(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return {
        "command": " ".join(shlex.quote(part) for part in command),
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "returncode": result.returncode,
    }


def _show_command(board: str, task_id: str) -> list[str]:
    return ["hermes", "kanban", "--board", board, "show", task_id, "--json"]


def _runs_command(board: str, task_id: str) -> list[str]:
    return ["hermes", "kanban", "--board", board, "runs", task_id, "--json"]


def _specify_command(board: str, task_id: str) -> list[str]:
    return ["hermes", "kanban", "--board", board, "specify", task_id, "--json"]


def _shell_join(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def _read_snapshot(
    board: str,
    task_id: str,
    *,
    show_json: str | None = None,
    runs_json: str | None = None,
) -> dict[str, Any]:
    show = _load_json(show_json) if show_json else _run_json_command(_show_command(board, task_id))
    runs = _load_json(runs_json) if runs_json else _run_json_command(_runs_command(board, task_id))
    return summarize_dispatch_progress(show=show, runs=runs, board=board)


def _poll_until_status(
    board: str,
    task_id: str,
    *,
    target_statuses: set[str],
    timeout_seconds: int,
    interval_seconds: float,
) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last = _read_snapshot(board, task_id)
    while True:
        if last["status"] in target_statuses:
            return last
        if time.time() >= deadline:
            return last
        time.sleep(interval_seconds)
        last = _read_snapshot(board, task_id)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Promote a Hermes Kanban triage task through the public CLI, then watch for runtime status."
    )
    parser.add_argument("--config", required=True, help="Path to project YAML config; loaded for project boundary validation.")
    parser.add_argument("--board", required=True, help="Hermes Kanban board slug.")
    parser.add_argument("--task-id", required=True, help="Hermes Kanban task id.")
    parser.add_argument("--promote", action="store_true", help="Run `hermes kanban specify` when the task is still in triage.")
    parser.add_argument("--dry-run", action="store_true", help="Render the public CLI commands without changing Kanban state.")
    parser.add_argument("--target-status", action="append", dest="target_statuses", help="Status to stop watching for. Repeatable or comma-separated.")
    parser.add_argument("--timeout-seconds", type=int, default=180, help="Maximum watch time after promotion.")
    parser.add_argument("--interval-seconds", type=float, default=5.0, help="Polling interval while watching.")
    parser.add_argument("--show-json", help="Fixture path for hermes kanban show --json output; intended for tests/dry-runs.")
    parser.add_argument("--runs-json", help="Fixture path for hermes kanban runs --json output; intended for tests/dry-runs.")
    parser.add_argument("--output", help="Write JSON report to this path instead of stdout.")
    return parser


def _normalize_targets(raw: Sequence[str] | None) -> set[str]:
    values: list[str] = []
    for item in raw or DEFAULT_TARGET_STATUSES:
        values.extend(part.strip() for part in item.split(","))
    return {value for value in values if value}


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # Load config even though this script only talks to public Hermes CLI. This
    # keeps project invocations anchored to the checked-in integration config.
    load_config(args.config)

    target_statuses = _normalize_targets(args.target_statuses)
    before = _read_snapshot(
        args.board,
        args.task_id,
        show_json=args.show_json,
        runs_json=args.runs_json,
    )
    specify_cmd = _specify_command(args.board, args.task_id)
    report: dict[str, Any] = {
        "task_id": args.task_id,
        "board": args.board,
        "dry_run": args.dry_run,
        "uses_public_cli": True,
        "direct_db_write": False,
        "imports_hermes_internals": False,
        "target_statuses": sorted(target_statuses),
        "before": before,
        "promotion": {
            "requested": bool(args.promote),
            "needed": before["status"] == "triage",
            "command": _shell_join(specify_cmd),
        },
    }

    if args.promote and before["status"] == "triage":
        if args.dry_run:
            after = before
        else:
            report["promotion"]["result"] = _run_text_command(specify_cmd)
            after = _poll_until_status(
                args.board,
                args.task_id,
                target_statuses=target_statuses,
                timeout_seconds=args.timeout_seconds,
                interval_seconds=args.interval_seconds,
            )
    elif args.show_json or args.runs_json or args.dry_run:
        after = before
    else:
        after = _poll_until_status(
            args.board,
            args.task_id,
            target_statuses=target_statuses,
            timeout_seconds=args.timeout_seconds,
            interval_seconds=args.interval_seconds,
        )

    report["after"] = after
    report["reached_target"] = after["status"] in target_statuses
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0 if report["reached_target"] or args.dry_run else 1


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
