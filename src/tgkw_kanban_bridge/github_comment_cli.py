from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence

from .bridge import load_config
from .runtime import (
    KanbanStatusSummary,
    render_github_audit_comment,
    render_github_comment_command,
)

DEFAULT_COMMENT_HEADER = "> 将作大匠｜gpt-5.5｜thinking档位未暴露"


def _default_body_file(output: str | None, task_id: str) -> Path:
    if output:
        return Path(output).with_suffix(".md")
    return Path(tempfile.gettempdir()) / f"tgkw-kanban-comment-{task_id}.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render or post a GitHub audit comment from a Kanban status summary.")
    parser.add_argument("--config", required=True, help="Path to project YAML config.")
    parser.add_argument("--status-json", required=True, help="Path to a status summary JSON file.")
    parser.add_argument("--issue-number", type=int, help="GitHub issue number. Defaults to source issue in status JSON.")
    parser.add_argument("--comment-header", default=DEFAULT_COMMENT_HEADER, help="Identity/model header for the comment.")
    parser.add_argument("--body-file", help="Path to write the markdown comment body.")
    parser.add_argument("--dry-run", action="store_true", help="Write/print the comment plan without posting to GitHub.")
    parser.add_argument("--output", help="Write JSON output to this path instead of stdout.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)
    status_data = json.loads(Path(args.status_json).read_text(encoding="utf-8"))
    summary = KanbanStatusSummary.from_dict(status_data)
    issue_number = args.issue_number or summary.source_issue_number
    body_file = Path(args.body_file) if args.body_file else _default_body_file(args.output, summary.task_id)

    comment_body = render_github_audit_comment(summary, header=args.comment_header)
    body_file.write_text(comment_body, encoding="utf-8")
    command = render_github_comment_command(config=config, issue_number=issue_number, body_file=body_file)

    payload = {
        "dry_run": args.dry_run,
        "issue_number": issue_number,
        "body_file": str(body_file),
        "comment_body": comment_body,
        "would_execute": command,
    }

    if not args.dry_run:
        result = subprocess.run(
            command,
            check=True,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        payload["executed"] = True
        payload["stdout"] = result.stdout.strip()

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
