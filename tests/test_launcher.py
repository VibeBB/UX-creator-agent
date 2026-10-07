"""ux_launcher.py behavior checks (no docker required — argv only)."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest
import scripts.run_in_locked_image as locked_image_runner

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


@pytest.mark.parametrize("operation", ["inspect", "pull"])
def test_plugin_launcher_image_timeout_fails_closed(
    operation: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _load_launcher()
    monkeypatch.setattr(module, "_docker", lambda: "docker")
    monkeypatch.setenv("UX_TOOLS_IMAGE", "example/ux-tools:latest")
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if operation == "inspect" or command[1:3] != ["image", "inspect"]:
            raise subprocess.TimeoutExpired(command, cast(float, kwargs["timeout"]))
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    expected = "docker image inspect" if operation == "inspect" else "docker pull"
    with pytest.raises(RuntimeError, match=f"{expected} timed out"):
        module._ensure_image(tmp_path)
    assert len(calls) == (1 if operation == "inspect" else 2)


@pytest.mark.parametrize("operation", ["inspect", "pull"])
def test_locked_image_runner_timeouts(operation: str, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(_name: str) -> str:
        return "docker"

    monkeypatch.setattr(locked_image_runner.shutil, "which", fake_which)
    monkeypatch.setenv("UX_TOOLS_IMAGE", "example/ux-tools:latest")
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if operation == "inspect" or command[1:3] != ["image", "inspect"]:
            raise subprocess.TimeoutExpired(command, cast(float, kwargs["timeout"]))
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(locked_image_runner.subprocess, "run", fake_run)
    expected = "docker image inspect" if operation == "inspect" else "docker pull"
    with pytest.raises(RuntimeError, match=f"{expected} timed out"):
        locked_image_runner.main(["--", "true"])
    assert len(calls) == (1 if operation == "inspect" else 2)


def test_docker_argv_always_passes_workspace_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _load_launcher()
    monkeypatch.setenv("OPENHANDS_PROJECT_DIR", str(tmp_path))
    argv = module._docker_argv("example/ux-tools:latest", None, ["python", "-m", "ux_creator"])
    assert argv.count(f"OPENHANDS_PROJECT_DIR={tmp_path}") == 1


def test_locked_image_runner_passes_workspace_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_which(_name: str) -> str:
        return "docker"

    monkeypatch.setattr(locked_image_runner.shutil, "which", fake_which)
    monkeypatch.setenv("UX_TOOLS_IMAGE", "example/ux-tools:latest")
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(locked_image_runner.subprocess, "run", fake_run)
    assert locked_image_runner.main(["--", "true"]) == 0
    assert f"OPENHANDS_PROJECT_DIR={locked_image_runner.ROOT}" in calls[-1]


def test_container_user_rootless(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rootless daemons get 0:0 — the host uid maps to an unusable subuid."""
    module = _load_launcher()
    monkeypatch.setattr(
        module,
        "_docker_info_security_options",
        lambda: '["name=seccomp,profile=builtin","name=rootless","name=cgroupns"]',
    )
    assert module._container_user() == "0:0"
    argv = module._docker_argv("example/ux-tools:latest", None, ["doctor"])
    assert argv[argv.index("--user") + 1] == "0:0"


def test_container_user_rootful(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rootful daemons keep the invoking uid:gid so artifacts stay user-owned."""
    module = _load_launcher()
    monkeypatch.setattr(
        module,
        "_docker_info_security_options",
        lambda: '["name=seccomp,profile=builtin"]',
    )
    assert module._container_user() == f"{os.getuid()}:{os.getgid()}"


def test_container_user_docker_info_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """docker absent/failing -> keep the current uid:gid behavior."""
    module = _load_launcher()
    monkeypatch.setattr(module, "_docker_info_security_options", lambda: None)
    assert module._container_user() == f"{os.getuid()}:{os.getgid()}"


def test_run_in_locked_image_container_user(monkeypatch: pytest.MonkeyPatch) -> None:
    """scripts/run_in_locked_image.py shares the same rootless rule."""
    runner = cast(Any, locked_image_runner)
    monkeypatch.setattr(
        runner,
        "_docker_info_security_options",
        lambda: '["name=rootless"]',
    )
    assert runner._container_user() == "0:0"
    monkeypatch.setattr(runner, "_docker_info_security_options", lambda: None)
    assert runner._container_user() == f"{os.getuid()}:{os.getgid()}"
