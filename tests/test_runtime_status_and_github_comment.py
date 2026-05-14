import json
from pathlib import Path

from tgkw_kanban_bridge.bridge import load_config
from tgkw_kanban_bridge.runtime import (
    render_github_audit_comment,
    render_github_comment_command,
    summarize_kanban_task,
)


ROOT = Path(__file__).resolve().parents[1]
HEADER = "> 将作大匠｜gpt-5.5｜thinking档位未暴露"


def load_fixture(name: str):
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


def test_summarize_kanban_task_infers_source_issue_and_idempotency_key():
    config = load_config(ROOT / "configs" / "tiangongkaiwu.yaml")
    show = load_fixture("kanban_show_task_100.json")
    runs = load_fixture("kanban_runs_task_100.json")

    summary = summarize_kanban_task(show=show, runs=runs, board="tiangongkaiwu", config=config)

    assert summary.task_id == "t_ba44492a"
    assert summary.board == "tiangongkaiwu"
    assert summary.status == "triage"
    assert summary.assignee == "jiangzuodajiang"
    assert summary.tenant == "clawhub-system"
    assert summary.source_issue_url == "https://github.com/GTZhou/TianGongKaiWu/issues/100"
    assert summary.source_issue_number == 100
    assert summary.idempotency_key == "github:GTZhou/TianGongKaiWu#100"
    assert summary.run_count == 1
    assert summary.latest_run_summary == "example runtime closeout"


def test_render_github_audit_comment_contains_required_audit_fields():
    config = load_config(ROOT / "configs" / "tiangongkaiwu.yaml")
    summary = summarize_kanban_task(
        show=load_fixture("kanban_show_task_100.json"),
        runs=load_fixture("kanban_runs_task_100.json"),
        board="tiangongkaiwu",
        config=config,
    )

    comment = render_github_audit_comment(summary, header=HEADER)

    assert comment.startswith(HEADER)
    assert "## Hermes Kanban 运行态回写" in comment
    assert "task id：`t_ba44492a`" in comment
    assert "board：`tiangongkaiwu`" in comment
    assert "status：`triage`" in comment
    assert "assignee：`jiangzuodajiang`" in comment
    assert "idempotency-key：`github:GTZhou/TianGongKaiWu#100`" in comment
    assert "source issue：https://github.com/GTZhou/TianGongKaiWu/issues/100" in comment
    assert "latest run：example runtime closeout" in comment
    assert "不直接写 `kanban.db`" in comment


def test_render_github_comment_command_uses_isolated_gh_wrapper():
    config = load_config(ROOT / "configs" / "tiangongkaiwu.yaml")

    command = render_github_comment_command(
        config=config,
        issue_number=100,
        body_file=Path("/tmp/tgkw-comment.md"),
    )

    assert command == (
        "HOME=/home/zhouyu /home/zhouyu/.local/bin/gh-jiangzuodajiang "
        "issue comment 100 --repo GTZhou/TianGongKaiWu --body-file /tmp/tgkw-comment.md"
    )
    assert "token" not in command.lower()
    assert "cookie" not in command.lower()


def test_status_cli_outputs_summary_from_fixtures(tmp_path):
    from tgkw_kanban_bridge.status_cli import main

    output_path = tmp_path / "status.json"
    exit_code = main([
        "--config", str(ROOT / "configs" / "tiangongkaiwu.yaml"),
        "--board", "tiangongkaiwu",
        "--task-id", "t_ba44492a",
        "--show-json", str(ROOT / "fixtures" / "kanban_show_task_100.json"),
        "--runs-json", str(ROOT / "fixtures" / "kanban_runs_task_100.json"),
        "--output", str(output_path),
    ])

    assert exit_code == 0
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["task_id"] == "t_ba44492a"
    assert data["idempotency_key"] == "github:GTZhou/TianGongKaiWu#100"


def test_github_comment_cli_dry_run_outputs_comment_without_posting(tmp_path):
    from tgkw_kanban_bridge.github_comment_cli import main

    status_path = tmp_path / "status.json"
    output_path = tmp_path / "comment-plan.json"
    status_path.write_text(json.dumps({
        "task_id": "t_ba44492a",
        "title": "example",
        "board": "tiangongkaiwu",
        "status": "triage",
        "assignee": "jiangzuodajiang",
        "tenant": "clawhub-system",
        "idempotency_key": "github:GTZhou/TianGongKaiWu#100",
        "source_issue_url": "https://github.com/GTZhou/TianGongKaiWu/issues/100",
        "source_issue_number": 100,
        "run_count": 1,
        "latest_run_summary": "example runtime closeout",
    }, ensure_ascii=False), encoding="utf-8")

    exit_code = main([
        "--config", str(ROOT / "configs" / "tiangongkaiwu.yaml"),
        "--status-json", str(status_path),
        "--issue-number", "100",
        "--comment-header", HEADER,
        "--dry-run",
        "--output", str(output_path),
    ])

    assert exit_code == 0
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["dry_run"] is True
    assert data["would_execute"].endswith("issue comment 100 --repo GTZhou/TianGongKaiWu --body-file " + data["body_file"])
    assert "task id：`t_ba44492a`" in data["comment_body"]
