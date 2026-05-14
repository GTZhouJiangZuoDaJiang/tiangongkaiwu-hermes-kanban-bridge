import json
from pathlib import Path

from tgkw_kanban_bridge.bridge import build_plan, load_config, render_kanban_command


ROOT = Path(__file__).resolve().parents[1]


def load_fixture(name: str) -> dict:
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


def test_config_loads_tiangongkaiwu_mapping():
    config = load_config(ROOT / "configs" / "tiangongkaiwu.yaml")

    assert config.board.slug == "tiangongkaiwu"
    assert config.github.repo == "GTZhou/TianGongKaiWu"
    assert config.github.gh_command == "HOME=/home/zhouyu /home/zhouyu/.local/bin/gh-jiangzuodajiang"
    assert config.defaults.tenant == "clawhub-system"
    assert config.profiles["将作大匠"] == "jiangzuodajiang"


def test_build_plan_generates_idempotent_kanban_task_from_issue_fixture():
    config = load_config(ROOT / "configs" / "tiangongkaiwu.yaml")
    issue = load_fixture("github_issue_100.json")

    plan = build_plan(issue=issue, config=config, assignee_role="将作大匠")

    assert plan.title == "[子议题] 建立独立 GitHub 仓库开发测试 Hermes Kanban 集成方案"
    assert plan.board == "tiangongkaiwu"
    assert plan.assignee == "jiangzuodajiang"
    assert plan.tenant == "clawhub-system"
    assert plan.workspace == "dir:/home/zhouyu/repos/JiangZuoDaJiang/TianGongKaiWu"
    assert plan.idempotency_key == "github:GTZhou/TianGongKaiWu#100"
    assert "GitHub: https://github.com/GTZhou/TianGongKaiWu/issues/100" in plan.body
    assert "Acceptance:" in plan.body
    assert "不直接写 `kanban.db`" in plan.body


def test_render_kanban_command_uses_public_cli_surface_only():
    config = load_config(ROOT / "configs" / "tiangongkaiwu.yaml")
    issue = load_fixture("github_issue_100.json")
    plan = build_plan(issue=issue, config=config, assignee_role="将作大匠")

    command = render_kanban_command(plan)

    assert command[:4] == ["hermes", "kanban", "--board", "tiangongkaiwu"]
    assert "create" in command
    assert "--idempotency-key" in command
    assert "github:GTZhou/TianGongKaiWu#100" in command
    assert "--json" in command
    body_index = command.index("--body")
    executable_surface = command[:body_index]
    assert all("kanban.db" not in part for part in executable_surface)
    assert all("sqlite" not in part.lower() for part in executable_surface)


def test_render_kanban_command_can_park_task_in_triage():
    config = load_config(ROOT / "configs" / "tiangongkaiwu.yaml")
    issue = load_fixture("github_issue_100.json")
    plan = build_plan(issue=issue, config=config, assignee_role="将作大匠", triage=True)

    command = render_kanban_command(plan)

    assert "--triage" in command


def test_dry_run_cli_outputs_plan_without_executing_hermes(tmp_path):
    from tgkw_kanban_bridge.cli import main

    output_path = tmp_path / "plan.json"
    exit_code = main([
        "--config", str(ROOT / "configs" / "tiangongkaiwu.yaml"),
        "--issue-json", str(ROOT / "fixtures" / "github_issue_100.json"),
        "--assignee-role", "将作大匠",
        "--dry-run",
        "--output", str(output_path),
    ])

    assert exit_code == 0
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["dry_run"] is True
    assert data["would_execute"][0:2] == ["hermes", "kanban"]
    assert data["plan"]["idempotency_key"] == "github:GTZhou/TianGongKaiWu#100"
