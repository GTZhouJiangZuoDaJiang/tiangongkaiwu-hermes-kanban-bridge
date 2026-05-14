import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_NAMES = [
    "github-issue-to-kanban",
    "kanban-task-status",
    "kanban-to-github-comment",
    "kanban-promote-watch",
]


def _symlink_required_tool(tmp_bin: Path, source: str, target_name: str | None = None) -> None:
    resolved = shutil.which(source)
    assert resolved is not None, f"required test tool not found: {source}"
    os.symlink(resolved, tmp_bin / (target_name or source))


def _run_script_help_checks(tmp_path: Path, python_link_name: str) -> None:
    tmp_bin = tmp_path / "bin"
    tmp_bin.mkdir()
    _symlink_required_tool(tmp_bin, "bash")
    _symlink_required_tool(tmp_bin, "dirname")
    os.symlink(sys.executable, tmp_bin / python_link_name)

    env = {
        "HOME": str(tmp_path),
        "PATH": str(tmp_bin),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
    }

    for script_name in SCRIPT_NAMES:
        script = ROOT / "scripts" / script_name
        result = subprocess.run(
            [str(script), "--help"],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
            check=False,
        )

        assert result.returncode == 0, (
            f"{script_name} failed without python on PATH\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        assert "python: not found" not in result.stderr


def test_script_wrappers_prefer_python3_when_python_is_missing(tmp_path):
    """Script entrypoints should work on Debian/Ubuntu hosts without `python`."""
    _run_script_help_checks(tmp_path, "python3")


def test_script_wrappers_fall_back_to_python_when_python3_is_missing(tmp_path):
    """Script entrypoints should still work in older envs that only expose `python`."""
    _run_script_help_checks(tmp_path, "python")
