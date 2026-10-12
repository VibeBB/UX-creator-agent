"""mruby/c UX manifests.

The UX agent authors `*.rb` UX logic for firmware that embeds mruby/c.
It then emits a ``*.mruby-manifest.json`` next to the sources: the
firmware contract pins that file by sha256 (``mrubyc.ux_manifest``) and
its ``requires`` block must fit the VM feature flags the contract
configures (``use_float``/``use_math``/``use_string``/``use_utf8``/
``no_timer``).

``detect_requires`` mirrors the feature scan in the firmware gate so a
manifest generated here is never rejected for under-declared features.
Everything here is deterministic; stale manifests and undeclared files
are failures, not warnings.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .mruby_api import detect_classes

# Kept in lockstep with firmware's feature_scan patterns.
_FLOAT_RE = re.compile(r"(?<![\w.'])\d+\.\d+(?![\w'])|\.to_f\b|\bFloat\b")
_MATH_RE = re.compile(r"\bMath\.")
_STRING_RE = re.compile(
    r"\bString\b|\.to_s\b|\.(size|length|strip|lstrip|rstrip|split|gsub|sub|upcase|"
    r"downcase|chars|bytes|slice|index|rindex|start_with\?|end_with\?|include\?|"
    r"center|ljust|rjust|tr|chomp|chop|reverse|succ|ord|chr|hex|oct|format|sprintf|"
    r"capitalize|swapcase|count|delete|squeeze|insert|replace|empty\?|eql\?)\b|#\{"
)
_TICK_RE = re.compile(r"\bVM\.tick\b|\bsleep_ms\b|\bVM\.sleep\b|(^|[^.\w])sleep\b")

MANIFEST_SUFFIX = ".mruby-manifest.json"
DSL_SUFFIX = ".ux.rb"


class MrubyRequires(BaseModel):
    """VM features the firmware contract must enable."""

    model_config = ConfigDict(extra="forbid")

    float: int = Field(default=0, ge=0, le=2)
    math: bool = False
    string: bool = True
    utf8: bool = False
    tick: bool = True


class MrubyManifestFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class MrubyManifest(BaseModel):
    """The ``*.mruby-manifest.json`` document firmware pins."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    artifact_kind: str = "mruby_manifest"
    product: str = Field(min_length=1)
    files: list[MrubyManifestFile]
    requires: MrubyRequires = Field(default_factory=MrubyRequires)
    classes: list[str] = Field(default_factory=list[str])


def detect_requires(source: str) -> MrubyRequires:
    """Declared VM features a source needs (unioned across files)."""
    return MrubyRequires(
        float=1 if _FLOAT_RE.search(source) else 0,
        math=bool(_MATH_RE.search(source)),
        string=bool(_STRING_RE.search(source)),
        utf8=any(ord(ch) > 127 for ch in source),
        tick=bool(_TICK_RE.search(source)),
    )


def _merge_requires(a: MrubyRequires, b: MrubyRequires) -> MrubyRequires:
    return MrubyRequires(
        float=max(a.float, b.float),
        math=a.math or b.math,
        string=a.string or b.string,
        utf8=a.utf8 or b.utf8,
        tick=a.tick or b.tick,
    )


def list_ruby_sources(directory: Path) -> list[Path]:
    """``*.rb`` sources under ``directory``; ``*.ux.rb`` DSL files excluded."""
    return sorted(
        p for p in directory.glob("*.rb") if p.is_file() and not p.name.endswith(DSL_SUFFIX)
    )


def build_manifest(
    product: str,
    sources: list[Path],
    root: Path,
    requires: MrubyRequires | None = None,
) -> MrubyManifest:
    """Deterministic manifest: sorted files, sha256, unioned requires."""
    files: list[MrubyManifestFile] = []
    merged = requires or MrubyRequires(string=False, tick=False)
    for source in sorted(sources, key=lambda p: p.as_posix()):
        blob = source.read_bytes()
        files.append(
            MrubyManifestFile(
                file=source.relative_to(root).as_posix(),
                sha256=hashlib.sha256(blob).hexdigest(),
            )
        )
        merged = _merge_requires(merged, detect_requires(blob.decode("utf-8", "replace")))
    classes = sorted(
        {
            name
            for source in sources
            for name in detect_classes(source.read_text(encoding="utf-8", errors="replace"))
        }
    )
    return MrubyManifest(product=product, files=files, requires=merged, classes=classes)


def render_manifest(manifest: MrubyManifest) -> str:
    return manifest.model_dump_json(indent=2) + "\n"


def manifest_problems(path: Path, root: Path) -> list[str]:
    """Static gate over an existing manifest: parse, freshness, coverage."""
    problems: list[str] = []
    try:
        manifest = MrubyManifest.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"{path.name} unreadable: {exc}"]
    listed = {entry.file for entry in manifest.files}
    for entry in manifest.files:
        source = (root / entry.file).resolve()
        if not source.is_file():
            problems.append(f"{entry.file} listed but missing")
            continue
        actual = hashlib.sha256(source.read_bytes()).hexdigest()
        if actual != entry.sha256:
            problems.append(f"{entry.file} stale; regenerate {path.name}")
            continue
        needed = detect_requires(source.read_text(encoding="utf-8", errors="replace"))
        if needed.float > manifest.requires.float:
            problems.append(
                f"{entry.file} uses Float but manifest declares float={manifest.requires.float}"
            )
        if needed.math and not manifest.requires.math:
            problems.append(f"{entry.file} uses Math but manifest declares math=false")
        if needed.string and not manifest.requires.string:
            problems.append(f"{entry.file} uses String but manifest declares string=false")
        if needed.utf8 and not manifest.requires.utf8:
            problems.append(f"{entry.file} is non-ASCII but manifest declares utf8=false")
        if needed.tick and not manifest.requires.tick:
            problems.append(f"{entry.file} uses VM.tick/sleep but manifest declares tick=false")
    for extra in list_ruby_sources(path.parent):
        rel = extra.relative_to(root).as_posix() if extra.is_relative_to(root) else extra.name
        if rel not in listed:
            problems.append(f"{rel} not listed in {path.name}; regenerate")
    return problems
