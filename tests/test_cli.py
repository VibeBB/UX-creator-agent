"""CLI smoke tests (deterministic paths only — no ruby/mmdc/java needed)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ux_creator import cli, doctor

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


def test_cli_boundary_error_includes_exception_type(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail(_args: object) -> int:
        raise RuntimeError("unexpected failure")

    monkeypatch.setattr(cli, "_cmd_doctor", fail)
    assert cli.main(["doctor"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["error_type"] == "RuntimeError"
    assert payload["detail"] == "unexpected failure"


def test_doctor_probe_reports_unexpected_import_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(_name: str) -> object:
        raise RuntimeError("module initialization failed")

    monkeypatch.setattr(doctor.importlib, "import_module", fail)
    report = doctor.run_doctor()
    checks = report["checks"]
    check = next(item for item in checks if item["capability"] == "pydantic")

    assert check["status"] == "fail"
    assert "RuntimeError" in check["detail"]
