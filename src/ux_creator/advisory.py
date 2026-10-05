"""Typed advisory review records (L2 only — never verdicts).

A vision-capable reviewer writes `review-visual-<slug>.advisory.json`
next to `ux-report.json`; `parse_visual_review` validates the detail so a
malformed model answer can never masquerade as a record (returns `None`).
Same contract shape as wire's `src/wire/advisory.py`.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .contract import UXContract
from .gates import GateCheck, GateReport

VISION_REVIEW_TOOL = "vision_review"
IMPRESSION_MIN_LENGTH = 240
_SENTENCE_MARKS = "。.!?"

VisualChecklist = Literal[
    "journey_map",
    "statechart",
    "wireframe",
    "intake_image",
    "service_blueprint",
    "emotion_curve",
    "production_plan",
    "sister_artifact",
]
VisualFindingCategory = Literal[
    "missing_touchpoint",
    "broken_flow",
    "unreachable_state",
    "label_collision",
    "text_outside_frame",
    "illegible",
    "ambiguous_notation",
    "missing_element",
    "design_intent",
    "other",
]


class VisualFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: VisualFindingCategory
    severity: Literal["info", "minor", "major"] = "info"
    where: str = ""
    observation: str = Field(min_length=1)
    suggestion: str = ""


class VisualReviewDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checklist: VisualChecklist
    image_path: str = Field(min_length=1)
    image_sha256: str = Field(min_length=1)
    model: str = ""
    findings: list[VisualFinding] = Field(default_factory=list[VisualFinding])


class AdvisoryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str = VISION_REVIEW_TOOL
    stage: str = "review"
    status: Literal["ok", "error", "not_applicable"]
    summary: str = ""
    artifacts: list[str] = Field(default_factory=list[str])
    detail: VisualReviewDetail | IntakeDetail | dict[str, Any] | None = None


def _sentence_count(text: str) -> int:
    return len([m for m in _SENTENCE_MARKS if m in text]) or (1 if text.strip() else 0)


def parse_visual_review(payload: dict[str, Any]) -> AdvisoryResult | None:
    """Validate a visual-review record; None when malformed (fail-closed)."""
    try:
        record = AdvisoryResult.model_validate(payload)
    except ValidationError:
        return None
    if record.status == "ok":
        if (
            len(record.summary.strip()) < IMPRESSION_MIN_LENGTH
            or _sentence_count(record.summary) < 2
        ):
            return None
        if not isinstance(record.detail, VisualReviewDetail):
            return None
    return record


def write_visual_review(
    image: Path,
    checklist: VisualChecklist,
    summary: str,
    findings: list[VisualFinding],
    model: str = "",
) -> Path:
    """Compute the image sha256 and write the sibling advisory record."""
    path = _visual_review_path(image)
    detail = VisualReviewDetail(
        checklist=checklist,
        image_path=str(image),
        image_sha256=f"sha256:{hashlib.sha256(image.read_bytes()).hexdigest()}",
        model=model,
        findings=findings,
    )
    record = AdvisoryResult(status="ok", summary=summary, artifacts=[str(image)], detail=detail)
    path.write_text(
        json.dumps(record.model_dump(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def write_visual_review_not_applicable(
    image: Path, checklist: VisualChecklist, summary: str
) -> Path:
    """Record that no vision-capable review could be performed on an image."""
    if not image.is_file():
        raise FileNotFoundError(f"image artifact does not exist: {image}")
    path = _visual_review_path(image)
    record = AdvisoryResult(
        status="not_applicable",
        summary=summary,
        artifacts=[str(image)],
        detail={"checklist": checklist},
    )

    path.write_text(
        json.dumps(record.model_dump(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def _visual_review_path(image: Path) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "-", image.stem.lower()).strip("-") or "image"
    return image.parent / f"review-visual-{slug}.advisory.json"


Reconciliation = Literal["corroborated", "contradicted", "unverifiable"]


class ReconciledFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record: str
    checklist: VisualChecklist
    category: VisualFindingCategory
    severity: Literal["info", "minor", "major"]
    where: str
    reconciliation: Reconciliation
    reason: str


def load_visual_reviews(
    out_dir: Path,
) -> tuple[list[tuple[Path, AdvisoryResult]], list[Path]]:
    """Parse every review-visual-*.advisory.json under out_dir.

    Returns (valid records, malformed paths). Malformed files are listed,
    never raised — a broken advisory file must not break the report.
    """

    ok: list[tuple[Path, AdvisoryResult]] = []
    malformed: list[Path] = []
    for path in sorted(out_dir.glob("review-visual-*.advisory.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            malformed.append(path)
            continue
        record = parse_visual_review(payload)
        if record is None:
            malformed.append(path)
        else:
            ok.append((path, record))
    return ok, malformed


def reconcile_findings(
    contract: UXContract,
    gate_report: GateReport,
    records: list[tuple[Path, AdvisoryResult]],
) -> list[ReconciledFinding]:
    """Check L2 visual findings against deterministic contract/gate truth."""
    states: dict[str, str] = {}  # state id -> chart id
    transitions: set[tuple[str, str]] = set()
    for chart in contract.statecharts:
        for s in chart.states:
            states[s.id] = chart.id
        for t in chart.transitions:
            transitions.add((t.from_state, t.to))
    extracted = {tok for ref in contract.imports for tok in ref.extracted}
    touchpoints = {
        tp for journey in contract.journeys for stage in journey.stages for tp in stage.touchpoints
    }

    def reach_checks(chart_id: str) -> list[GateCheck]:
        return [c for c in gate_report.checks if c.id == f"statechart.{chart_id}.reachability"]

    findings: list[ReconciledFinding] = []
    for path, record in records:
        if record.status != "ok" or not isinstance(record.detail, VisualReviewDetail):
            continue
        for f in record.detail.findings:
            where = f.where.strip().lower()
            state_ref = where.rsplit(".", 1)[-1]
            reconciliation: Reconciliation = "unverifiable"
            reason = "visual-only category"
            if f.category == "unreachable_state":
                chart_id = states.get(state_ref)
                if chart_id is None:
                    reason = f"state {state_ref!r} not declared in any statechart"
                else:
                    checks = reach_checks(chart_id)
                    failed_detail = next((c.detail for c in checks if c.status == "fail"), "")
                    if failed_detail and state_ref in {
                        s.strip() for s in failed_detail.partition(":")[2].split(",")
                    }:
                        reconciliation, reason = (
                            "corroborated",
                            f"gates confirm {state_ref} unreachable in {chart_id}",
                        )
                    elif checks and all(c.status == "pass" for c in checks):
                        reconciliation, reason = (
                            "contradicted",
                            f"gates prove {state_ref} reachable in {chart_id}",
                        )
                    else:
                        reason = f"no reachability verdict for {chart_id}"
            elif f.category == "missing_touchpoint":
                if where in touchpoints:
                    reconciliation, reason = (
                        "contradicted",
                        f"{where} is a declared stage touchpoint",
                    )
                elif where in extracted:
                    reconciliation, reason = (
                        "corroborated",
                        f"{where} was imported but is not wired into any stage",
                    )
                else:
                    reason = f"{where!r} is neither a touchpoint nor an import"
            elif f.category == "broken_flow":
                m = re.fullmatch(r"([a-z0-9_]+)\s*->\s*([a-z0-9_]+)", where)
                if m and (m.group(1), m.group(2)) in transitions:
                    reconciliation, reason = (
                        "contradicted",
                        f"transition {m.group(1)}->{m.group(2)} exists",
                    )
                elif m and m.group(1) in states and m.group(2) in states:
                    reconciliation, reason = (
                        "corroborated",
                        f"no transition {m.group(1)}->{m.group(2)} though both states exist",
                    )
                else:
                    reason = f"{where!r} is not a resolvable from->to pair"
            findings.append(
                ReconciledFinding(
                    record=str(path),
                    checklist=record.detail.checklist,
                    category=f.category,
                    severity=f.severity,
                    where=f.where,
                    reconciliation=reconciliation,
                    reason=reason,
                )
            )
    findings.sort(key=lambda r: (r.record, r.category, r.where))
    return findings


INTAKE_TOOL = "ux.intake_touchpoints"


class TouchpointCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    surface: str = ""
    evidence: str = Field(min_length=1)
    confidence: Literal["low", "medium", "high"] = "medium"


class IntakeDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_path: str
    image_sha256: str
    model: str = ""
    candidates: list[TouchpointCandidate]


class IntakeReconciliation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    declared: list[str]
    undeclared: list[str]
    unobserved: list[str]
    surface_mismatch: list[str]
    malformed: list[str]


def normalize_touchpoint(text: str) -> str:
    """lowercase, [^a-z0-9]+ -> _, stripped — the canonical touchpoint id."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def parse_intake_record(payload: dict[str, Any]) -> AdvisoryResult | None:
    """Validate an intake-touchpoints record; None when malformed."""
    try:
        record = AdvisoryResult.model_validate(payload)
    except ValidationError:
        return None
    if record.tool != INTAKE_TOOL or record.stage != "intake":
        return None
    if record.status == "ok":
        if not isinstance(record.detail, IntakeDetail):
            # detail may arrive as dict on re-parse; coerce once
            try:
                detail = IntakeDetail.model_validate(record.detail)
            except ValidationError:
                return None
            record.detail = detail
        if not record.detail.candidates:
            return None
        for candidate in record.detail.candidates:
            if not normalize_touchpoint(candidate.id):
                return None
    return record


def write_intake_record(
    image: Path,
    candidates: list[TouchpointCandidate],
    model: str = "",
) -> Path:
    """Compute the image sha256 and write the sibling intake record."""
    slug = re.sub(r"[^a-z0-9]+", "-", image.stem.lower()).strip("-") or "image"
    detail = IntakeDetail(
        image_path=str(image),
        image_sha256=f"sha256:{hashlib.sha256(image.read_bytes()).hexdigest()}",
        model=model,
        candidates=candidates,
    )
    record = AdvisoryResult(
        tool=INTAKE_TOOL,
        stage="intake",
        status="ok",
        summary="intake touchpoint candidates",
        artifacts=[str(image)],
        detail=detail,
    )
    path = image.parent / f"intake-touchpoints-{slug}.advisory.json"
    path.write_text(
        json.dumps(record.model_dump(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def load_intake_records(
    out_dir: Path,
) -> tuple[list[tuple[Path, AdvisoryResult]], list[Path]]:
    """Parse every intake-touchpoints-*.advisory.json; malformed listed, never raised."""
    ok: list[tuple[Path, AdvisoryResult]] = []
    malformed: list[Path] = []
    for path in sorted(out_dir.glob("intake-touchpoints-*.advisory.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            malformed.append(path)
            continue
        record = parse_intake_record(payload)
        if record is None:
            malformed.append(path)
        else:
            ok.append((path, record))
    return ok, malformed


def reconcile_intake(
    contract: UXContract,
    records: list[tuple[Path, AdvisoryResult]],
) -> IntakeReconciliation:
    """Compare observed intake touchpoints with declared stage touchpoints."""
    declared = {
        normalize_touchpoint(tp)
        for journey in contract.journeys
        for stage in journey.stages
        for tp in stage.touchpoints
    }
    # candidate id -> surfaces claimed by images (deduped, sorted)
    seen: dict[str, set[str]] = {}
    for _path, record in records:
        if record.status != "ok" or not isinstance(record.detail, IntakeDetail):
            continue
        for cand in record.detail.candidates:
            cid = normalize_touchpoint(cand.id)
            if not cid:
                continue
            seen.setdefault(cid, set())
            if cand.surface:
                seen[cid].add(cand.surface)
    observed = set(seen)
    # stage surfaces per declared touchpoint id
    tp_surfaces: dict[str, set[str]] = {}
    for journey in contract.journeys:
        for stage in journey.stages:
            for tp in stage.touchpoints:
                tp_surfaces.setdefault(normalize_touchpoint(tp), set()).update(stage.surfaces)
    surface_mismatch: list[str] = []
    for cid in sorted(observed & declared):
        for surf in sorted(seen[cid]):
            contract_surfaces = sorted(tp_surfaces.get(cid, set()))
            if contract_surfaces and surf not in contract_surfaces:
                surface_mismatch.append(
                    f"{cid}: image says {surf}, contract stage.surfaces has "
                    f"[{', '.join(contract_surfaces)}]"
                )
    return IntakeReconciliation(
        declared=sorted(observed & declared),
        undeclared=sorted(observed - declared),
        unobserved=sorted(declared - observed),
        surface_mismatch=sorted(surface_mismatch),
        malformed=[],
    )
