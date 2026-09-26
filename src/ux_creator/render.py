"""Render Mermaid and PlantUML projections to images via subprocesses.

`mmdc` (mermaid-cli) and `java -jar $PLANTUML_JAR` run as unmodified
external tools. A missing tool never crashes the pipeline: the check
records `unknown` in the render report instead (fail-closed).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RenderResult:
    source: Path
    output: Path | None
    status: str  # "ok" | "unknown"
    detail: str


def _plantuml_jar() -> Path | None:
    env = os.environ.get("PLANTUML_JAR")
    if env:
        jar = Path(env)
        return jar if jar.is_file() else None
    default = Path("/opt/plantuml/plantuml.jar")
    return default if default.is_file() else None


def _mmdc_cmd(mmdc: str, source: Path, output: Path) -> list[str]:
    cmd = [mmdc, "-i", str(source), "-o", str(output), "-b", "transparent"]
    config = os.environ.get("PUPPETEER_CONFIG")
    if config and Path(config).is_file():
        cmd += ["-p", config]
    return cmd


def render_mermaid(source: Path, out_dir: Path, fmt: str = "svg") -> RenderResult:
    mmdc = shutil.which("mmdc")
    output = out_dir / f"{source.stem}.{fmt}"
    if mmdc is None:
        return RenderResult(source, None, "unknown", "mmdc not on PATH")
    proc = subprocess.run(
        _mmdc_cmd(mmdc, source, output),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not output.is_file():
        return RenderResult(source, None, "unknown", proc.stderr.strip() or "mmdc failed")
    return RenderResult(source, output, "ok", "")


def render_plantuml(source: Path, out_dir: Path, fmt: str = "svg") -> RenderResult:
    java = shutil.which("java")
    jar = _plantuml_jar()
    if java is None:
        return RenderResult(source, None, "unknown", "java not on PATH")
    if jar is None:
        return RenderResult(source, None, "unknown", "PLANTUML_JAR not set / jar missing")
    proc = subprocess.run(
        [java, "-jar", str(jar), f"-t{fmt}", "-output", str(out_dir), str(source)],
        capture_output=True,
        text=True,
        check=False,
    )
    output = out_dir / f"{source.stem}.{fmt}"
    if proc.returncode != 0 or not output.is_file():
        return RenderResult(source, None, "unknown", proc.stderr.strip() or "plantuml failed")
    return RenderResult(source, output, "ok", "")


def render_all(out_dir: Path, fmt: str = "svg") -> list[RenderResult]:
    """Render every *.mmd and *.puml under out_dir. Missing tools → unknown."""
    results: list[RenderResult] = []
    for source in sorted(out_dir.glob("*.mmd")):
        results.append(render_mermaid(source, out_dir, fmt))
    for source in sorted(out_dir.glob("*.puml")):
        results.append(render_plantuml(source, out_dir, fmt))
    return results
