from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

from .bridge import build_plan, load_config, render_kanban_command


def _load_issue_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _fetch_issue_with_gh(gh_command: str, repo: str, issue_number: int) -> dict[str, Any]:
    json_fields = "number,title,body,url,labels"
    jq = (
        "{number,title,body,html_url:.url,"
        "labels:[.labels[]? | {name:.name}],"
        "repository:{full_name:\"" + repo + "\"}}"
    )
    shell_command = " ".join(
        [
            gh_command,
            "issue",
            "view",
            shlex.quote(str(issue_number)),
            "--repo",
            shlex.quote(repo),
            "--json",
            shlex.quote(json_fields),
            "--jq",
            shlex.quote(jq),
        ]
    )
    result = subprocess.run(
        shell_command,
        check=True,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return json.loads(result.stdout)


def _json_payload(plan, command: list[str], dry_run: bool) -> dict[str, Any]:
    return {
        "dry_run": dry_run,
        "plan": plan.to_dict(),
        "would_execute": command,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create or dry-run a Hermes Kanban task from a GitHub issue."
    )
    parser.add_argument("--config", required=True, help="Path to project YAML config.")
    parser.add_argument("--issue-json", help="Path to a local GitHub issue JSON fixture.")
    parser.add_argument("--repo", help="GitHub repo, e.g. GTZhou/TianGongKaiWu.")
    parser.add_argument("--issue-number", type=int, help="GitHub issue number to read via gh.")
    parser.add_argument("--assignee-role", default="将作大匠", help="Role key from config profiles.")
    parser.add_argument("--dry-run", action="store_true", help="Print/write plan without executing Hermes.")
    parser.add_argument("--triage", action="store_true", help="Create the Kanban task in triage to avoid dispatcher pickup.")
    parser.add_argument("--output", help="Write JSON output to this path instead of stdout.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)

    if args.issue_json:
        issue = _load_issue_json(args.issue_json)
    elif args.repo and args.issue_number:
        issue = _fetch_issue_with_gh(
            gh_command=config.github.gh_command,
            repo=args.repo,
            issue_number=args.issue_number,
        )
    else:
        parser.error("Provide either --issue-json or both --repo and --issue-number.")

    plan = build_plan(
        issue=issue,
        config=config,
        assignee_role=args.assignee_role,
        triage=args.triage,
    )
    command = render_kanban_command(plan)
    payload = _json_payload(plan, command, dry_run=args.dry_run)

    if not args.dry_run:
        result = subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE)
        payload["executed"] = True
        payload["stdout"] = result.stdout

    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
