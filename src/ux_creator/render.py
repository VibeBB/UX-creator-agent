"""Render Mermaid and PlantUML projections to images via subprocesses.

`mmdc` (mermaid-cli) and `java -jar $PLANTUML_JAR` run as unmodified
external tools. A missing or hung tool never crashes the pipeline: the check
records `unknown` in the render report instead (fail-closed).
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .sisters import SHA256, TargetAgent
from .workspace import workspace_path


class ImageIdentity(BaseModel):
    """A producer's image claim, bound to one resolved path and byte revision."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    path: str = Field(min_length=1)
    sha256: str = Field(pattern=SHA256.pattern)
    owner_plugin: Literal["ux"] | TargetAgent
    origin: Literal["renderer", "liaison-response"]


class ImageDetail(BaseModel):
    """An explicitly auxiliary view, never an additional formal product output."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    path: str = Field(min_length=1)
    parents: list[str] = Field(min_length=1, max_length=16)
    operation: Literal["crop", "tile", "composite"]

    @model_validator(mode="after")
    def _arity(self) -> ImageDetail:
        if self.operation != "composite" and len(self.parents) != 1:
            raise ValueError("crop/tile needs exactly one parent")
        return self


class DerivedImageIdentity(BaseModel):
    """Hash-bound declared ancestry; it does not certify a pixel transformation."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    path: str = Field(min_length=1)
    sha256: str = Field(pattern=SHA256.pattern)
    owner_plugin: Literal["ux"] = "ux"
    origin: Literal["derived"] = "derived"
    operation: Literal["crop", "tile", "composite"]
    parents: list[ImageIdentity] = Field(min_length=1, max_length=16)

    @model_validator(mode="after")
    def _parents(self) -> DerivedImageIdentity:
        paths = [parent.path for parent in self.parents]
        if len(set(paths)) != len(paths) or self.path in paths:
            raise ValueError("ancestry must name unique original parents")
        if self.operation != "composite" and len(paths) != 1:
            raise ValueError("crop/tile needs exactly one original parent")
        return self


@dataclass(frozen=True)
class RenderResult:
    source: Path
    output: Path | None
    status: str  # "ok" | "unknown"
    detail: str
    image_identity: ImageIdentity | DerivedImageIdentity | None = None


def with_image_details(
    renders: list[RenderResult], details: list[ImageDetail], root: Path
) -> list[RenderResult]:
    """Bind auxiliary bytes only to intact originals from this producer response."""
    originals = {
        str(r.output.resolve()): r.image_identity
        for r in renders
        if r.status == "ok" and r.output and isinstance(r.image_identity, ImageIdentity)
    }
    results = list(renders)
    seen = set(originals)
    for detail in details:
        path = workspace_path(detail.path, root)
        if str(path) in seen:
            raise ValueError("image detail cannot replace an original or duplicate a path")
        parents: list[ImageIdentity] = []
        for source in detail.parents:
            parent = workspace_path(source, root)
            identity = originals.get(str(parent))
            if (
                identity is None
                or hashlib.sha256(parent.read_bytes()).hexdigest() != identity.sha256
            ):
                raise ValueError("image detail parent is not an intact producer original")
            parents.append(identity)
        derived = DerivedImageIdentity(
            path=str(path),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            parents=parents,
            operation=detail.operation,
        )
        results.append(RenderResult(path, path, "ok", "declared auxiliary ancestry", derived))
        seen.add(str(path))
    return results


def _rendered(source: Path, output: Path) -> RenderResult:
    try:
        with output.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
    except OSError as exc:
        return RenderResult(source, None, "unknown", f"rendered output unavailable: {exc}")
    identity = ImageIdentity(
        path=str(output.resolve()), sha256=digest, owner_plugin="ux", origin="renderer"
    )
    return RenderResult(source, output, "ok", "", identity)


def _plantuml_jar() -> Path | None:
    env = os.environ.get("PLANTUML_JAR")
    if env:
        jar = Path(env)
        return jar if jar.is_file() else None
    default = Path("/opt/plantuml/plantuml.jar")
    return default if default.is_file() else None


def _mmdc_cmd(mmdc: str, source: Path, output: Path, fmt: str) -> list[str]:
    background = "white" if fmt == "png" else "transparent"
    cmd = [mmdc, "-i", str(source), "-o", str(output), "-b", background]
    if fmt == "png":
        cmd += ["-s", "2"]
    config = os.environ.get("PUPPETEER_CONFIG")
    if config and Path(config).is_file():
        cmd += ["-p", config]
    return cmd


def _render_output_path(source: Path, out_dir: Path, fmt: str) -> Path:
    output = out_dir / f"{source.stem}.{fmt}"
    if source.suffix in {".mmd", ".puml"}:
        other_suffix = ".puml" if source.suffix == ".mmd" else ".mmd"
        if (out_dir / f"{source.stem}{other_suffix}").is_file():
            return out_dir / f"{source.name}.{fmt}"
    return output


def render_mermaid(
    source: Path, out_dir: Path, fmt: str = "svg", timeout: int = 60
) -> RenderResult:
    mmdc = shutil.which("mmdc")
    output = _render_output_path(source, out_dir, fmt)
    if mmdc is None:
        return RenderResult(source, None, "unknown", "mmdc not on PATH")
    try:
        proc = subprocess.run(
            _mmdc_cmd(mmdc, source, output, fmt),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return RenderResult(source, None, "unknown", "mmdc timed out")
    if proc.returncode != 0 or not output.is_file():
        return RenderResult(source, None, "unknown", proc.stderr.strip() or "mmdc failed")
    return _rendered(source, output)


def render_plantuml(
    source: Path, out_dir: Path, fmt: str = "svg", timeout: int = 60
) -> RenderResult:
    java = shutil.which("java")
    jar = _plantuml_jar()
    output = _render_output_path(source, out_dir, fmt)
    if java is None:
        return RenderResult(source, None, "unknown", "java not on PATH")
    if jar is None:
        return RenderResult(source, None, "unknown", "PLANTUML_JAR not set / jar missing")
    try:
        with tempfile.TemporaryDirectory(prefix=".plantuml-", dir=out_dir) as temp_dir:
            proc = subprocess.run(
                [
                    java,
                    "-jar",
                    str(jar),
                    f"-t{fmt}",
                    "-output",
                    temp_dir,
                    str(source.resolve()),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout,
            )
            rendered = Path(temp_dir) / f"{source.stem}.{fmt}"
            if proc.returncode == 0 and rendered.is_file():
                os.replace(rendered, output)
    except subprocess.TimeoutExpired:
        return RenderResult(source, None, "unknown", "plantuml timed out")
    if proc.returncode != 0 or not output.is_file():
        return RenderResult(source, None, "unknown", proc.stderr.strip() or "plantuml failed")
    return _rendered(source, output)


def render_all(
    out_dir: Path, fmts: Sequence[str] = ("svg", "png"), timeout: int = 60
) -> list[RenderResult]:
    """Render every *.mmd and *.puml under out_dir. Missing tools → unknown."""
    results: list[RenderResult] = []
    for source in sorted(out_dir.glob("*.mmd")):
        for fmt in fmts:
            results.append(render_mermaid(source, out_dir, fmt, timeout=timeout))
    for source in sorted(out_dir.glob("*.puml")):
        for fmt in fmts:
            results.append(render_plantuml(source, out_dir, fmt, timeout=timeout))
    return results
