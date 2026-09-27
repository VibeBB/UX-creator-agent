"""CLI smoke tests (deterministic paths only — no ruby/mmdc/java needed)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CONTRACT = "examples/smart-kettle/smart-kettle.ux.json"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ux_creator", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_gates_pass() -> None:
    proc = _run("gates", CONTRACT)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert json.loads(proc.stdout)["verdict"] == "pass"


def test_author_writes_projections(tmp_path: Path) -> None:
    out = tmp_path / "out"
    proc = _run("author", CONTRACT, "--out", str(out))
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert (out / "ux-report.json").is_file()
    assert (out / "provenance.json").is_file()


def test_from_ruby_missing_tool_or_ok(tmp_path: Path) -> None:
    out = tmp_path / "x.ux.json"
    proc = _run("from-ruby", "examples/smart-kettle/smart-kettle.ux.rb", "--out", str(out))
    # host may lack ruby: either a pass with written file or a fail verdict
    payload = json.loads(proc.stdout)
    if payload["verdict"] == "pass":
        assert out.is_file()
    else:
        assert payload["stage"] == "from-ruby"
