"""Tests for ux_creator.render subprocess handling."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from ux_creator import render
from ux_creator.contract import UXContract
from ux_creator.gates import run_gates
from ux_creator.report import build_report


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


def test_render_all_renders_each_source_in_every_format(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mermaid = tmp_path / "journey.mmd"
    plantuml = tmp_path / "statechart.puml"
    mermaid.write_text("graph TD; A-->B;", encoding="utf-8")
    plantuml.write_text("@startuml\nA -> B\n@enduml", encoding="utf-8")
    calls: list[tuple[str, str]] = []

    def fake_mermaid(source: Path, _out_dir: Path, fmt: str, timeout: int = 60):
        calls.append((source.suffix, fmt))
        return render.RenderResult(source, None, "unknown", "")

    def fake_plantuml(source: Path, _out_dir: Path, fmt: str, timeout: int = 60):
        calls.append((source.suffix, fmt))
        return render.RenderResult(source, None, "unknown", "")

    monkeypatch.setattr(render, "render_mermaid", fake_mermaid)
    monkeypatch.setattr(render, "render_plantuml", fake_plantuml)

    results = render.render_all(tmp_path)

    assert calls == [
        (".mmd", "svg"),
        (".mmd", "png"),
        (".puml", "svg"),
        (".puml", "png"),
    ]
    assert len(results) == 4


def test_same_stem_mermaid_and_plantuml_renders_have_distinct_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mermaid = tmp_path / "diagram.mmd"
    plantuml = tmp_path / "diagram.puml"
    mermaid.write_text("graph TD; A-->B;", encoding="utf-8")
    plantuml.write_text("@startuml\nA -> B\n@enduml", encoding="utf-8")
    jar = tmp_path / "plantuml.jar"
    jar.write_text("fake", encoding="utf-8")

    def fake_which(name: str) -> str:
        return f"/fake/{name}"

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        command = args[0]
        if command[0] == "/fake/mmdc":
            output = Path(command[command.index("-o") + 1])
        else:
            output_dir = Path(command[command.index("-output") + 1])
            fmt = command[command.index("-jar") + 2].removeprefix("-t")
            output = output_dir / f"diagram.{fmt}"
        output.write_bytes(b"rendered")
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(render.shutil, "which", fake_which)
    monkeypatch.setattr(render, "_plantuml_jar", lambda: jar)
    monkeypatch.setattr(render.subprocess, "run", fake_run)

    results = render.render_all(tmp_path)

    assert [result.output for result in results] == [
        tmp_path / "diagram.mmd.svg",
        tmp_path / "diagram.mmd.png",
        tmp_path / "diagram.puml.svg",
        tmp_path / "diagram.puml.png",
    ]
    assert all(result.status == "ok" for result in results)


def test_mermaid_background_and_scale_are_format_specific(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "diagram.mmd"
    source.write_text("graph TD; A-->B;", encoding="utf-8")
    recorded: list[list[str]] = []

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        command = args[0]
        recorded.append(command)
        output = Path(command[command.index("-o") + 1])
        output.write_text("<svg/>", encoding="utf-8")
        return subprocess.CompletedProcess(args=command, returncode=0)

    def fake_which(_name: str) -> str:
        return "/fake/mmdc"

    monkeypatch.setattr(render.shutil, "which", fake_which)
    monkeypatch.setattr(render.subprocess, "run", fake_run)

    assert render.render_mermaid(source, tmp_path, fmt="svg").status == "ok"
    assert render.render_mermaid(source, tmp_path, fmt="png").status == "ok"

    svg, png = recorded
    assert svg[svg.index("-b") + 1] == "transparent"
    assert "-s" not in svg
    assert png[png.index("-b") + 1] == "white"
    assert png[png.index("-s") + 1] == "2"


def test_report_preserves_both_render_formats(example_contract: UXContract, tmp_path: Path) -> None:
    renders = [
        render.RenderResult(Path("journey.mmd"), Path("journey.svg"), "ok", ""),
        render.RenderResult(Path("journey.mmd"), Path("journey.png"), "ok", ""),
    ]

    report = build_report(example_contract, run_gates(example_contract), renders)

    assert [entry["output"] for entry in report["renders"]] == [
        "journey.svg",
        "journey.png",
    ]


def test_report_review_coverage_counts_svg_png_pair_once(
    example_contract: UXContract, tmp_path: Path
) -> None:
    (tmp_path / "statechart.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "statechart.png").write_bytes(b"png")

    report = build_report(example_contract, run_gates(example_contract), out_dir=tmp_path)

    assert report["lenses"]["review"]["images_without_record"] == [str(tmp_path / "statechart.png")]
