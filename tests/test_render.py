"""Tests for ux_creator.render subprocess handling."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from ux_creator import render


def test_render_mermaid_timeout_is_unknown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "diagram.mmd"
    source.write_text("graph TD; A-->B;")

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd=["mmdc"], timeout=1)

    def fake_which(name: str) -> str:
        return "/fake/mmdc"

    monkeypatch.setattr(render.shutil, "which", fake_which)
    monkeypatch.setattr(render.subprocess, "run", fake_run)

    result = render.render_mermaid(source, tmp_path)
    assert result.status == "unknown"
    assert result.output is None
    assert "timed out" in result.detail


def test_render_plantuml_timeout_is_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "diagram.puml"
    source.write_text("@startuml\nA -> B\n@enduml")
    jar = tmp_path / "plantuml.jar"
    jar.write_text("fake")
    recorded: dict[str, Any] = {}

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        recorded.update(kwargs)
        raise subprocess.TimeoutExpired(cmd=["java"], timeout=1)

    def fake_which(name: str) -> str:
        return "/fake/java"

    monkeypatch.setattr(render.shutil, "which", fake_which)
    monkeypatch.setattr(render, "_plantuml_jar", lambda: jar)
    monkeypatch.setattr(render.subprocess, "run", fake_run)

    result = render.render_plantuml(source, tmp_path, timeout=3)
    assert result.status == "unknown"
    assert result.output is None
    assert "timed out" in result.detail
    assert recorded["timeout"] == 3


def test_render_mermaid_missing_tool_is_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "diagram.mmd"
    source.write_text("graph TD; A-->B;")

    def fake_which(name: str) -> None:
        return None

    monkeypatch.setattr(render.shutil, "which", fake_which)

    result = render.render_mermaid(source, tmp_path)
    assert result.status == "unknown"
    assert result.detail == "mmdc not on PATH"


def test_render_passes_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "diagram.mmd"
    source.write_text("graph TD; A-->B;")
    recorded: dict[str, Any] = {}

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        recorded.update(kwargs)
        (tmp_path / f"{source.stem}.svg").write_text("<svg/>")
        return subprocess.CompletedProcess(args=args[0] if args else [], returncode=0)

    def fake_which(name: str) -> str:
        return "/fake/mmdc"

    monkeypatch.setattr(render.shutil, "which", fake_which)
    monkeypatch.setattr(render.subprocess, "run", fake_run)

    result = render.render_mermaid(source, tmp_path, timeout=7)
    assert result.status == "ok"
    assert recorded["timeout"] == 7
