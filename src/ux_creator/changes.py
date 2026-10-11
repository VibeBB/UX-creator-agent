"""Family change control: ECR/ECO records and their deterministic closure check.

An ECR names the hash-pinned workspace files a change touches. The ECO that
implements it lists every changed file with its before/after sha256, the gate
report that passed it, and the AI design-review findings with dispositions.
``check_eco`` re-derives the impact from the workspace pin graph, so a
consumer that still pins an old hash, or changed without being listed, fails.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, model_validator

from .gates import FAIL, PASS, UNKNOWN, CheckStatus, GateCheck

SHA256 = r"^[0-9a-f]{64}$"
_HEX = re.compile(r"^[0-9a-f]{64}$")
_SKIP_DIRS = {".git", "node_modules", "out", ".venv", "observations"}
_MIN_TEXT = 12


class FileRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=SHA256)


class ECR(BaseModel):
    """Engineering change request: why, what is proposed, which pinned files."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["vibebb.ecr/v1"]
    id: str = Field(pattern=r"^ECR-[0-9]+$")
    origin: str = Field(min_length=1)
    reason: str = Field(min_length=_MIN_TEXT)
    proposal: str = Field(min_length=_MIN_TEXT)
    items: list[FileRef] = Field(min_length=1)
    raised_by: str | None = Field(default=None, pattern=r"^ECO-[0-9]+$")
    created_at: AwareDatetime


class Change(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    path: str = Field(min_length=1)
    before: str = Field(pattern=SHA256)
    after: str = Field(pattern=SHA256)
    gate_report: FileRef

    @model_validator(mode="after")
    def _changed(self) -> Change:
        if self.before == self.after:
            raise ValueError(f"{self.path}: before and after sha256 are equal")
        return self


class Finding(BaseModel):
    """One AI design-review finding; reviewers may only push toward stopping."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str = Field(pattern=r"^F[0-9]+$")
    reviewer: str = Field(min_length=1)
    severity: Literal["blocker", "major", "minor"]
    subject: str = Field(min_length=1)
    text: str = Field(min_length=_MIN_TEXT)
    disposition: Literal["open", "fixed", "accepted"]
    resolution: str = ""


class Review(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    reviewers: list[str] = Field(min_length=1)
    findings: list[Finding] = Field(default_factory=list[Finding])


class ECO(BaseModel):
    """Engineering change order: the applied, gated and reviewed change."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["vibebb.eco/v1"]
    id: str = Field(pattern=r"^ECO-[0-9]+$")
    ecr: FileRef
    author: str = Field(min_length=1)
    changes: list[Change] = Field(min_length=1)
    review: Review
    created_at: AwareDatetime

    @model_validator(mode="after")
    def _unique(self) -> ECO:
        paths = [c.path for c in self.changes]
        if len(paths) != len(set(paths)):
            raise ValueError("changes: duplicate path")
        ids = [f.id for f in self.review.findings]
        if len(ids) != len(set(ids)):
            raise ValueError("review.findings: duplicate id")
        return self


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel(path: Path, workspace: Path) -> str:
    return path.resolve().relative_to(workspace.resolve()).as_posix()


def _json_files(workspace: Path) -> list[Path]:
    return sorted(
        path
        for path in workspace.rglob("*.json")
        if path.is_file() and not _SKIP_DIRS.intersection(path.relative_to(workspace).parts[:-1])
    )


def _resolve(value: str, base: Path, workspace: Path) -> str | None:
    root = workspace.resolve()
    for candidate in (base / value, workspace / value):
        try:
            resolved = candidate.resolve()
        except (OSError, RuntimeError):
            continue
        if resolved.is_relative_to(root) and resolved.is_file():
            return resolved.relative_to(root).as_posix()
    return None


def pins(workspace: Path) -> list[tuple[str, str, str]]:
    """``(consumer, target, pinned_sha256)`` for every path+sha256 pair in workspace JSON.

    A pin is a JSON object holding one 64-hex string and exactly one string
    that resolves to a workspace file; change records themselves are skipped.
    """
    found: set[tuple[str, str, str]] = set()
    for path in _json_files(workspace):
        if path.name.endswith((".ecr.json", ".eco.json")):
            continue
        try:
            payload: object = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        consumer = _rel(path, workspace)
        stack = [payload]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(cast(list[object], node))
                continue
            if not isinstance(node, dict):
                continue
            values = list(cast(dict[str, object], node).values())
            stack.extend(values)
            strings = [v for v in values if isinstance(v, str)]
            hashes = [v for v in strings if _HEX.match(v)]
            targets = {
                t
                for v in strings
                if not _HEX.match(v) and (t := _resolve(v, path.parent, workspace))
            }
            if len(hashes) == 1 and len(targets) == 1:
                found.add((consumer, targets.pop(), hashes[0]))
    return sorted(found)


def _load(model: type[ECR] | type[ECO], path: Path) -> ECR | ECO:
    return model.model_validate_json(path.read_text(encoding="utf-8"))


def _ecr_check(eco: ECO, workspace: Path) -> tuple[GateCheck, ECR | None]:
    path = workspace / eco.ecr.path
    if not path.is_file():
        return GateCheck("eco.ecr", eco.ecr.path, UNKNOWN, detail="ECR file missing"), None
    if _sha(path) != eco.ecr.sha256:
        return GateCheck("eco.ecr", eco.ecr.path, FAIL, detail="ECR changed after pinning"), None
    try:
        ecr = cast(ECR, _load(ECR, path))
    except (ValidationError, ValueError) as exc:
        return GateCheck("eco.ecr", eco.ecr.path, FAIL, detail=f"invalid ECR: {exc}"), None
    return GateCheck("eco.ecr", ecr.id, PASS, detail=ecr.reason), ecr


def _scope_checks(eco: ECO, ecr: ECR) -> list[GateCheck]:
    listed = {c.path: c for c in eco.changes}
    checks: list[GateCheck] = []
    for item in ecr.items:
        change = listed.get(item.path)
        if change is None:
            checks.append(GateCheck("eco.scope", item.path, FAIL, detail="ECR item not changed"))
        elif change.before != item.sha256:
            checks.append(
                GateCheck("eco.scope", item.path, FAIL, detail="before sha256 != ECR item sha256")
            )
        else:
            checks.append(GateCheck("eco.scope", item.path, PASS))
    return checks


def _applied_check(change: Change, workspace: Path) -> GateCheck:
    path = workspace / change.path
    if not path.is_file():
        return GateCheck("eco.applied", change.path, FAIL, detail="changed file missing")
    actual = _sha(path)
    status: CheckStatus = PASS if actual == change.after else FAIL
    return GateCheck("eco.applied", change.path, status, detail=f"sha256 {actual}")


def _evidence_check(change: Change, workspace: Path) -> GateCheck:
    ref = change.gate_report
    path = workspace / ref.path
    if not path.is_file():
        return GateCheck("eco.evidence", change.path, UNKNOWN, detail=f"{ref.path} missing")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ref.sha256:
        return GateCheck("eco.evidence", change.path, FAIL, detail=f"{ref.path} changed")
    try:
        report: object = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return GateCheck("eco.evidence", change.path, FAIL, detail=f"{ref.path}: {exc}")
    verdict = cast(dict[str, object], report).get("verdict") if isinstance(report, dict) else None
    if verdict != PASS:
        return GateCheck("eco.evidence", change.path, FAIL, detail=f"verdict {verdict!r}")
    if change.after not in raw.decode("utf-8"):
        return GateCheck(
            "eco.evidence", change.path, UNKNOWN, detail="report does not cite the after sha256"
        )
    return GateCheck("eco.evidence", change.path, PASS, detail=ref.path)


def _pin_checks(eco: ECO, workspace: Path) -> list[GateCheck]:
    changed = {c.path for c in eco.changes}
    checks: list[GateCheck] = []
    for consumer, target, pinned in pins(workspace):
        if target not in changed:
            continue
        subject = f"{consumer} -> {target}"
        if pinned != _sha(workspace / target):
            checks.append(GateCheck("eco.pins", subject, FAIL, detail="stale pin"))
        elif consumer not in changed:
            checks.append(
                GateCheck("eco.pins", subject, FAIL, detail="impacted consumer not in changes")
            )
        else:
            checks.append(GateCheck("eco.pins", subject, PASS))
    return checks


def _review_checks(eco: ECO) -> list[GateCheck]:
    review = eco.review
    independent = eco.author not in review.reviewers
    checks = [
        GateCheck(
            "dr.independence",
            ", ".join(review.reviewers),
            PASS if independent else FAIL,
            detail="" if independent else f"author {eco.author} reviewed its own change",
        )
    ]
    for finding in review.findings:
        problem = ""
        if finding.reviewer not in review.reviewers:
            problem = f"reviewer {finding.reviewer} is not listed"
        elif finding.disposition == "open":
            problem = "finding is open"
        elif finding.severity == "blocker" and finding.disposition != "fixed":
            problem = "a blocker can only be fixed"
        elif len(finding.resolution.strip()) < _MIN_TEXT:
            problem = "resolution is missing"
        checks.append(
            GateCheck(
                "dr.findings",
                finding.id,
                FAIL if problem else PASS,
                detail=problem or f"{finding.severity} {finding.disposition}",
            )
        )
    return checks


def _cycle_check(eco: ECO, workspace: Path) -> GateCheck:
    raised: dict[str, str | None] = {}
    eco_ecr: dict[str, str] = {}
    for path in _json_files(workspace):
        try:
            if path.name.endswith(".ecr.json"):
                ecr = cast(ECR, _load(ECR, path))
                raised[ecr.id] = ecr.raised_by
            elif path.name.endswith(".eco.json"):
                other = cast(ECO, _load(ECO, path))
                ecr_path = workspace / other.ecr.path
                if ecr_path.is_file():
                    eco_ecr[other.id] = cast(ECR, _load(ECR, ecr_path)).id
        except (OSError, ValidationError, ValueError):
            continue
    seen: list[str] = []
    node: str | None = eco.id
    while node is not None:
        if node in seen:
            return GateCheck("eco.cycle", eco.id, FAIL, detail=" -> ".join([*seen, node]))
        seen.append(node)
        ecr_id = eco_ecr.get(node)
        node = raised.get(ecr_id) if ecr_id is not None else None
    return GateCheck("eco.cycle", eco.id, PASS, detail=" -> ".join(seen))


def check_eco(eco_path: Path, workspace: Path) -> dict[str, Any]:
    """Deterministic ECO closure verdict; any ``unknown`` or ``fail`` fails."""
    checks: list[GateCheck] = []
    eco: ECO | None = None
    try:
        eco = cast(ECO, _load(ECO, eco_path))
    except (OSError, ValidationError, ValueError) as exc:
        checks.append(GateCheck("eco.record", str(eco_path), FAIL, detail=str(exc)))
    if eco is not None:
        ecr_check, ecr = _ecr_check(eco, workspace)
        checks.append(ecr_check)
        if ecr is not None:
            checks += _scope_checks(eco, ecr)
        for change in eco.changes:
            checks += [_applied_check(change, workspace), _evidence_check(change, workspace)]
        checks += _pin_checks(eco, workspace)
        checks += _review_checks(eco)
        checks.append(_cycle_check(eco, workspace))
    verdict = PASS if all(c.status == PASS for c in checks) else FAIL
    return {
        "schema_version": 1,
        "gate": "ux-creator.change",
        "eco": eco.id if eco is not None else None,
        "eco_sha256": _sha(eco_path) if eco_path.is_file() else None,
        "verdict": verdict,
        "checks": [
            {"id": c.id, "subject": c.subject, "status": c.status, "detail": c.detail}
            for c in checks
        ],
    }


__all__ = ["ECO", "ECR", "Change", "Finding", "Review", "check_eco", "pins"]
