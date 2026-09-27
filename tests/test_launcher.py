"""ux_launcher.py behavior checks (no docker required — argv only)."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "plugins" / "ux"
LAUNCHER = PLUGIN_ROOT / "scripts" / "ux_launcher.py"


def _load_launcher() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ux_launcher_test", LAUNCHER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_main_mcp_server_argv_is_module_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """`mcp_server` must exec `python -m ux_creator.mcp_server`; argv entries are str."""
    module = _load_launcher()
    captured: list[list[str]] = []

    def fake_execvp(file: str, args: list[str]) -> None:
        captured.append([file, *args])

    def fake_ensure_image(_root: Path, *, pull: bool = True) -> str:
        return "img@sha256:abc"

    def fake_resolve_source(_root: Path) -> Path | None:
        return None

    monkeypatch.setattr(module, "_ensure_image", fake_ensure_image)
    monkeypatch.setattr(module, "resolve_source", fake_resolve_source)
    monkeypatch.setattr(os, "execvp", fake_execvp)
    monkeypatch.setattr(sys, "argv", ["ux_launcher.py", "mcp_server", "--extra"])
    assert module.main() == 0
    assert len(captured) == 1
    argv = captured[0]
    assert argv[0] == "docker"
    assert all(isinstance(arg, str) for arg in argv)
    assert argv[-4:] == ["python", "-m", "ux_creator.mcp_server", "--extra"]


def test_warn_fallback_json_matches_doctor_key(capsys: pytest.CaptureFixture[str]) -> None:
    """The --warn fallback payload uses the same top-level key as ux_creator.doctor."""
    module = _load_launcher()
    assert module._warn_or_die("boom", ["doctor", "--warn"]) == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload == {"verdict": "fail", "detail": "boom"}
