"""Tests for the ux plugin hook scripts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).parents[1] / "plugins" / "ux" / "hooks" / "scripts"
PROTECT_SCRIPT = SCRIPTS / "protect_generated.py"
RAIL_SCRIPT = SCRIPTS / "safety_rail.py"
STATUS_SCRIPT = SCRIPTS / "report_ux_status.py"
PROFILES_SCRIPT = SCRIPTS / "ensure_llm_profiles.py"


def _run_hook(
    script: Path,
    payload: dict[str, Any] | str,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.pop("OPENHANDS_PROJECT_DIR", None)
    return subprocess.run(
        [sys.executable, str(script)],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_protect_blocks_projection_write() -> None:
    payload = {
        "tool_name": "file_editor",
        "tool_input": {"command": "create", "path": "out/x.smart-kettle.odi.csv"},
    }
    proc = _run_hook(PROTECT_SCRIPT, payload)
    assert proc.returncode == 2


def test_protect_blocks_report_write() -> None:
    payload = {
        "tool_name": "file_editor",
        "tool_input": {"command": "create", "path": "out/ux-report.json"},
    }
    assert _run_hook(PROTECT_SCRIPT, payload).returncode == 2


def test_protect_allows_contract_edit() -> None:
    payload = {
        "tool_name": "file_editor",
        "tool_input": {"command": "str_replace", "path": "smart-kettle.ux.json"},
    }
    assert _run_hook(PROTECT_SCRIPT, payload).returncode == 0


def test_protect_allows_terminal_read() -> None:
    payload = {
        "tool_name": "terminal",
        "tool_input": {"command": "cat out/ux-report.json"},
    }
    assert _run_hook(PROTECT_SCRIPT, payload).returncode == 0


def test_safety_rail_denies_rm_root() -> None:
    payload = {"tool_name": "terminal", "tool_input": {"command": "rm -rf /"}}
    assert _run_hook(RAIL_SCRIPT, payload).returncode == 2


def test_safety_rail_denies_push_main() -> None:
    payload = {"tool_name": "terminal", "tool_input": {"command": "git push origin main"}}
    assert _run_hook(RAIL_SCRIPT, payload).returncode == 2


def test_safety_rail_allows_pytest() -> None:
    payload = {"tool_name": "terminal", "tool_input": {"command": "uv run pytest -q"}}
    assert _run_hook(RAIL_SCRIPT, payload).returncode == 0


def test_report_status_no_reports(tmp_path: Path) -> None:
    proc = _run_hook(STATUS_SCRIPT, {"working_dir": str(tmp_path)})
    assert proc.returncode == 0
    out = json.loads(proc.stdout)
    assert out["decision"] == "allow"
    ctx = out["additionalContext"].lower()
    assert "no ux reports" in ctx or "no design reports" in ctx or "report" in ctx


def test_profiles_hook_exits_zero() -> None:
    proc = _run_hook(PROFILES_SCRIPT, {})
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["hook"] == "ensure-llm-profiles"
