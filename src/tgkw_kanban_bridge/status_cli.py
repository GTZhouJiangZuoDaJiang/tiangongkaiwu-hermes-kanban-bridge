from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

from .bridge import load_config
from .runtime import summarize_kanban_task


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize a Hermes Kanban task via public CLI JSON.")
    parser.add_argument("--config", required=True, help="Path to project YAML config.")
    parser.add_argument("--board", required=True, help="Hermes Kanban board slug.")
    parser.add_argument("--task-id", required=True, help="Hermes Kanban task id.")
    parser.add_argument("--show-json", help="Fixture path for hermes kanban show --json output.")
    parser.add_argument("--runs-json", help="Fixture path for hermes kanban runs --json output.")
    parser.add_argument("--output", help="Write JSON summary to this path instead of stdout.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)

    if args.show_json:
        show = _load_json(args.show_json)
    else:
        show = _run_json_command([
            "hermes",
            "kanban",
            "--board",
            args.board,
            "show",
            args.task_id,
            "--json",
        ])

    if args.runs_json:
        runs = _load_json(args.runs_json)
    else:
        runs = _run_json_command([
            "hermes",
            "kanban",
            "--board",
            args.board,
            "runs",
            args.task_id,
            "--json",
        ])

    summary = summarize_kanban_task(show=show, runs=runs, board=args.board, config=config)
    rendered = json.dumps(summary.to_dict(), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
