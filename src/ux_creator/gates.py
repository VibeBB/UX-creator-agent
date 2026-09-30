"""Deterministic UX gates — the only pass/fail authority.

Every check emits a structured result: status is "pass", "fail", or
"unknown"; "unknown" and "fail" both make the design verdict fail
(fail-closed). Thresholds are never relaxed to reach a pass.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Literal

from .contract import UXContract, contract_sha256

CheckStatus = Literal["pass", "fail", "unknown"]
Verdict = Literal["pass", "fail"]
PASS: Final = "pass"
FAIL: Final = "fail"
UNKNOWN: Final = "unknown"


@dataclass(frozen=True)
class GateCheck:
    id: str
    subject: str
    status: CheckStatus
    measured: float | None = None
    limit: float | None = None
    detail: str = ""


@dataclass(frozen=True)
class GateReport:
    checks: list[GateCheck]
    verdict: Verdict

    def to_dict(self, contract: UXContract) -> dict[str, Any]:
        summary = {
            PASS: sum(1 for c in self.checks if c.status == PASS),
            FAIL: sum(1 for c in self.checks if c.status == FAIL),
            UNKNOWN: sum(1 for c in self.checks if c.status == UNKNOWN),
        }
        return {
            "schema_version": 1,
            "gate": "ux-creator",
            "design": {
                "name": contract.product.name,
                "contract_sha256": contract_sha256(contract),
            },
            "verdict": self.verdict,
            "summary": summary,
            "checks": [
                {
                    "id": c.id,
                    "subject": c.subject,
                    "status": c.status,
                    "measured": c.measured,
                    "limit": c.limit,
                    "detail": c.detail,
                }
                for c in self.checks
            ],
        }


def _wrap(check_id: str, fn: Callable[..., list[GateCheck]], *args: Any) -> list[GateCheck]:
    try:
        return fn(*args)
    except Exception as exc:
        return [
            GateCheck(
                check_id,
                check_id,
                UNKNOWN,
                detail=f"check error: {type(exc).__name__}: {exc}",
            )
        ]


def _statechart_checks(contract: UXContract) -> list[GateCheck]:
    checks: list[GateCheck] = []
    for chart in contract.statecharts:
        state_ids = {s.id for s in chart.states}
        initials = [s.id for s in chart.states if s.initial]
        cid = f"statechart.{chart.id}"
        checks.append(
            GateCheck(
                f"{cid}.single_initial",
                chart.id,
                PASS if len(initials) == 1 else FAIL,
                measured=float(len(initials)),
                limit=1.0,
                detail=f"initial states: {initials or 'none'}",
            )
        )
        undefined = sorted(
            {t.from_state for t in chart.transitions if t.from_state not in state_ids}
            | {t.to for t in chart.transitions if t.to not in state_ids}
        )
        checks.append(
            GateCheck(
                f"{cid}.states_defined",
                chart.id,
                PASS if not undefined else FAIL,
                detail=f"undefined state refs: {', '.join(undefined)}" if undefined else "",
            )
        )
        adjacency: dict[str, set[str]] = {s: set() for s in state_ids}
        for t in chart.transitions:
            if t.from_state in adjacency and t.to in adjacency:
                adjacency[t.from_state].add(t.to)
        reachable: set[str] = set()
        frontier = set(initials)
        while frontier:
            node = frontier.pop()
            if node in reachable:
                continue
            reachable.add(node)
            frontier |= adjacency.get(node, set()) - reachable
        unreachable = sorted(state_ids - reachable)
        checks.append(
            GateCheck(
                f"{cid}.reachability",
                chart.id,
                PASS if not unreachable else FAIL,
                detail=f"unreachable: {', '.join(unreachable)}" if unreachable else "",
            )
        )
        finals = {s.id for s in chart.states if s.final}
        dead = sorted(s for s in state_ids - finals if not adjacency.get(s))
        checks.append(
            GateCheck(
                f"{cid}.no_dead_end",
                chart.id,
                PASS if not dead else FAIL,
                detail=f"non-final states with no exit: {', '.join(dead)}" if dead else "",
            )
        )
        collisions = sorted(
            {
                (t.from_state, t.event)
                for t in chart.transitions
                if sum(
                    1
                    for u in chart.transitions
                    if u.from_state == t.from_state and u.event == t.event
                )
                > 1
            }
        )
        bad = [
            f"{src}/{event}"
            for src, event in collisions
            if not all(
                t.guard.strip()
                for t in chart.transitions
                if t.from_state == src and t.event == event
            )
            or len({t.guard for t in chart.transitions if t.from_state == src and t.event == event})
            != sum(1 for t in chart.transitions if t.from_state == src and t.event == event)
        ]
        checks.append(
            GateCheck(
                f"{cid}.deterministic",
                chart.id,
                PASS if not bad else FAIL,
                detail=(
                    "shared (from,event) without distinct non-empty guards: " + ", ".join(bad)
                    if bad
                    else ""
                ),
            )
        )
        surface_ids = contract.surface_ids()
        bad_surfaces = sorted(
            f"{st.id}:{st.surface}"
            for st in chart.states
            if st.surface and st.surface not in surface_ids
        )
        checks.append(
            GateCheck(
                f"{cid}.state_surface_declared",
                chart.id,
                PASS if not bad_surfaces else FAIL,
                detail=(
                    f"states referencing undeclared surfaces: {', '.join(bad_surfaces)}"
                    if bad_surfaces
                    else ""
                ),
            )
        )
    if not contract.statecharts:
        checks.append(
            GateCheck("statechart.present", "statecharts", FAIL, detail="no statecharts declared")
        )
    return checks


def _journey_checks(contract: UXContract) -> list[GateCheck]:
    checks: list[GateCheck] = []
    surface_ids = contract.surface_ids()
    for journey in contract.journeys:
        jid = f"journey.{journey.id}"
        missing = sorted(
            {s for stage in journey.stages for s in stage.surfaces if s not in surface_ids}
        )
        checks.append(
            GateCheck(
                f"{jid}.surfaces_declared",
                journey.id,
                PASS if not missing else FAIL,
                detail=f"undeclared surfaces: {', '.join(missing)}" if missing else "",
            )
        )
        bare = [
            stage.id for stage in journey.stages if stage.emotion <= 2 and not stage.pain_points
        ]
        checks.append(
            GateCheck(
                f"{jid}.pain_points_recorded",
                journey.id,
                PASS if not bare else FAIL,
                detail=(
                    f"stages with emotion<=2 and no pain_point: {', '.join(bare)}" if bare else ""
                ),
            )
        )
    if not contract.journeys:
        checks.append(GateCheck("journey.present", "journeys", FAIL, detail="no journeys declared"))
    app_layers = {"web_ui", "smartphone_app", "pc_app"}
    has_app = any(s.layer in app_layers for s in contract.product.surfaces)
    if has_app:
        onboard = [
            stage.id
            for journey in contract.journeys
            for stage in journey.stages
            if stage.kind == "onboard"
        ]
        checks.append(
            GateCheck(
                "journey.onboarding_present",
                "journeys",
                PASS if onboard else FAIL,
                detail=(
                    "app surfaces declared but no onboard stage"
                    if not onboard
                    else f"onboard stages: {', '.join(onboard)}"
                ),
            )
        )
    return checks


def _job_checks(contract: UXContract) -> list[GateCheck]:
    checks: list[GateCheck] = []
    thin = [
        j.id
        for j in contract.jobs
        if not (j.functional.strip() and j.emotional.strip() and j.social.strip())
    ]
    checks.append(
        GateCheck(
            "jobs.three_dimensions",
            "jobs",
            PASS if contract.jobs and not thin else FAIL,
            detail=(
                "no jobs declared"
                if not contract.jobs
                else (f"jobs missing dimensions: {', '.join(thin)}" if thin else "")
            ),
        )
    )
    return checks


def _known_triggers(contract: UXContract) -> set[str]:
    events = {t.event for chart in contract.statecharts for t in chart.transitions}
    touchpoints = {
        tp for journey in contract.journeys for stage in journey.stages for tp in stage.touchpoints
    }
    return events | touchpoints


def _feedback_checks(contract: UXContract) -> list[GateCheck]:
    checks: list[GateCheck] = []
    surface_ids = contract.surface_ids()
    known = _known_triggers(contract)
    bad_surfaces = sorted(f.id for f in contract.feedback if f.surface not in surface_ids)
    checks.append(
        GateCheck(
            "feedback.surface_declared",
            "feedback",
            PASS if not bad_surfaces else FAIL,
            detail=(
                f"feedback on undeclared surfaces: {', '.join(bad_surfaces)}"
                if bad_surfaces
                else ""
            ),
        )
    )
    bad_triggers = sorted(f.id for f in contract.feedback if f.trigger not in known)
    checks.append(
        GateCheck(
            "feedback.trigger_known",
            "feedback",
            PASS if not bad_triggers else FAIL,
            detail=(
                f"feedback with unknown triggers: {', '.join(bad_triggers)}" if bad_triggers else ""
            ),
        )
    )
    bad_latency = sorted(
        f"{f.id}:{f.latency_ms}ms"
        for f in contract.feedback
        if f.latency_ms > 10000 or (f.latency_ms > 1000 and not f.progress_indicator)
    )
    worst = max((f.latency_ms for f in contract.feedback), default=None)
    checks.append(
        GateCheck(
            "feedback.latency_budget",
            "feedback",
            PASS if not bad_latency else FAIL,
            measured=float(worst) if worst is not None else None,
            limit=10000.0,
            detail=(
                "latency >1s without progress_indicator or >10s: " + ", ".join(bad_latency)
                if bad_latency
                else ""
            ),
        )
    )
    return checks


def _loop_checks(contract: UXContract) -> list[GateCheck]:
    checks: list[GateCheck] = []
    known = _known_triggers(contract)
    bad = sorted(
        f"{loop.id}:{step}" for loop in contract.loops for step in loop.steps if step not in known
    )
    checks.append(
        GateCheck(
            "loop.steps_known",
            "loops",
            PASS if not bad else FAIL,
            detail=f"loop steps unknown: {', '.join(bad)}" if bad else "",
        )
    )
    open_loops = sorted(
        loop.id
        for loop in contract.loops
        if loop.cadence in ("moment", "session") and not loop.reward.strip()
    )
    checks.append(
        GateCheck(
            "loop.closes",
            "loops",
            PASS if not open_loops else FAIL,
            detail=(
                f"moment/session loops without reward: {', '.join(open_loops)}"
                if open_loops
                else ""
            ),
        )
    )
    return checks


def _core_experience_checks(contract: UXContract) -> list[GateCheck]:
    return [
        GateCheck(
            "core_experience.non_empty",
            "core_experience",
            PASS if contract.core_experience.strip() else FAIL,
        )
    ]


def _import_checks(contract: UXContract, workspace: Path) -> list[GateCheck]:
    checks: list[GateCheck] = []
    for ref in contract.imports:
        path = workspace / ref.path
        cid = f"imports.{ref.system}:{Path(ref.path).name}"
        if not path.is_file():
            checks.append(
                GateCheck(cid, ref.path, UNKNOWN, detail="imported file missing in workspace")
            )
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        checks.append(
            GateCheck(
                cid,
                ref.path,
                PASS if digest == ref.sha256 else FAIL,
                detail=f"sha256 {digest[:12]}… vs declared {ref.sha256[:12]}…",
            )
        )
    return checks


def stage_job_coverage(contract: UXContract) -> dict[str, list[str]]:
    """job id -> sorted "journey.stage" ids that declare it in stage.jobs."""
    coverage: dict[str, set[str]] = {}
    for journey in contract.journeys:
        for stage in journey.stages:
            for job in stage.jobs:
                coverage.setdefault(job, set()).add(f"{journey.id}.{stage.id}")
    return {job: sorted(refs) for job, refs in sorted(coverage.items())}


def _opportunity_checks(contract: UXContract) -> list[GateCheck]:
    """Underserved-job coverage via stage.jobs linkage."""
    coverage = stage_job_coverage(contract)
    linked = set(coverage)
    linked_any = any(stage.jobs for j in contract.journeys for stage in j.stages)
    underserved = sorted(j.id for j in contract.jobs if j.served == "underserved")
    uncovered = [j for j in underserved if j not in linked]
    checks = [
        GateCheck(
            "opportunity.coverage",
            "jobs",
            PASS if not uncovered else FAIL,
            detail=(
                f"uncovered underserved: {', '.join(uncovered)}"
                if uncovered
                else "no underserved jobs"
                if not underserved
                else ""
            ),
        )
    ]
    if contract.jobs and not linked_any:
        checks.append(
            GateCheck(
                "opportunity.stage_links",
                "jobs",
                FAIL,
                detail="no stage declares jobs — link stages to jobs",
            )
        )
    else:
        checks.append(GateCheck("opportunity.stage_links", "jobs", PASS))
    return checks


def run_gates(contract: UXContract, workspace: Path | None = None) -> GateReport:
    checks: list[GateCheck] = []
    checks += _wrap("statechart", _statechart_checks, contract)
    checks += _wrap("journey", _journey_checks, contract)
    checks += _wrap("jobs", _job_checks, contract)
    checks += _wrap("opportunity", _opportunity_checks, contract)
    checks += _wrap("feedback", _feedback_checks, contract)
    checks += _wrap("hig", _hig_checks, contract)
    checks += _wrap("loops", _loop_checks, contract)
    checks += _wrap("core_experience", _core_experience_checks, contract)
    if contract.cmf is not None:
        checks += _wrap("cmf", _cmf_checks, contract)
    if contract.content:
        checks += _wrap("content", _content_checks, contract)
    if contract.imports:
        checks += _wrap("imports", _import_checks, contract, workspace or Path.cwd())
    verdict: Verdict = PASS if all(c.status == PASS for c in checks) else FAIL
    return GateReport(checks=checks, verdict=verdict)


MIN_TARGET_MM = 7.8  # 44pt @163ppi
_TARGET_KINDS = {"button", "touch", "dial", "switch"}


def _rel_luminance(hex6: str) -> float:
    def channel(v: float) -> float:
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (int(hex6[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(fg: str, bg: str) -> float:
    """WCAG 2.x contrast ratio of two #RRGGBB colors."""
    l1, l2 = sorted((_rel_luminance(fg), _rel_luminance(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def _hig_checks(contract: UXContract) -> list[GateCheck]:
    sized = [
        c
        for c in contract.controls
        if c.kind in _TARGET_KINDS and (c.width_mm is not None or c.height_mm is not None)
    ]
    too_small = [
        f"{c.id}:{c.width_mm}x{c.height_mm}"
        for c in sized
        if (c.width_mm is not None and c.width_mm < MIN_TARGET_MM)
        or (c.height_mm is not None and c.height_mm < MIN_TARGET_MM)
    ]
    smallest = min(
        (min(v for v in (c.width_mm, c.height_mm) if v is not None) for c in sized),
        default=None,
    )
    checks = [
        GateCheck(
            "hig.target_size",
            "controls",
            FAIL if too_small else PASS,
            measured=smallest,
            limit=MIN_TARGET_MM,
            detail=(
                f"undersized controls: {', '.join(too_small)}"
                if too_small
                else "no undersized controls"
                if sized
                else "no sized controls"
            ),
        )
    ]
    colored = [c for c in contract.controls if c.fg and c.bg]
    ratios = {c.id: round(contrast_ratio(c.fg, c.bg), 2) for c in colored}
    failing = [
        f"{cid}:{ratio}"
        for cid, ratio in sorted(ratios.items())
        if ratio < (3.0 if next(c for c in colored if c.id == cid).large_text else 4.5)
    ]
    checks.append(
        GateCheck(
            "hig.contrast",
            "controls",
            FAIL if failing else PASS,
            measured=min(ratios.values(), default=None),
            limit=4.5,
            detail=(
                f"low contrast: {', '.join(failing)}"
                if failing
                else "no low-contrast controls"
                if colored
                else "no colored controls"
            ),
        )
    )
    return checks


CMF_SURFACE_LAYERS = frozenset({"hardware", "mechanism", "industrial_design"})
MIN_MARKING_CONTRAST = 3.0  # WCAG 1.4.11 non-text / large-text contrast


def _cmf_checks(contract: UXContract) -> list[GateCheck]:
    cmf = contract.cmf
    if cmf is None:
        return []
    covered = {p.surface for p in cmf.parts}
    physical = sorted(s.id for s in contract.product.surfaces if s.layer in CMF_SURFACE_LAYERS)
    missing = [sid for sid in physical if sid not in covered]
    checks = [
        GateCheck(
            "cmf.part_coverage",
            "cmf",
            FAIL if missing else PASS,
            measured=float(len(physical) - len(missing)),
            limit=float(len(physical)),
            detail=(
                f"physical surfaces without a CMF part: {', '.join(missing)}"
                if missing
                else f"{len(physical)} physical surfaces covered"
            ),
        )
    ]
    primaries = [c.id for c in cmf.palette if c.role == "primary"]
    checks.append(
        GateCheck(
            "cmf.primary_color",
            "cmf",
            PASS if primaries else FAIL,
            measured=float(len(primaries)),
            limit=1.0,
            detail="" if primaries else "palette has no primary color",
        )
    )
    hexes = {c.id: c.hex for c in cmf.palette}
    part_colors: dict[str, list[str]] = {}
    for part in cmf.parts:
        part_colors.setdefault(part.surface, []).append(hexes[part.color])
    ratios: dict[str, float] = {}
    unknown: list[str] = []
    for marking in cmf.markings:
        if not marking.color:
            continue
        backgrounds = part_colors.get(marking.surface, [])
        if not backgrounds:
            unknown.append(marking.id)
            continue
        ratios[marking.id] = round(
            min(contrast_ratio(hexes[marking.color], bg) for bg in backgrounds), 2
        )
    low = [f"{mid}:{r}" for mid, r in sorted(ratios.items()) if r < MIN_MARKING_CONTRAST]
    if low:
        status: CheckStatus = FAIL
        detail = f"low-contrast markings: {', '.join(low)}"
    elif unknown:
        status = UNKNOWN
        detail = f"markings on surfaces without a CMF part: {', '.join(sorted(unknown))}"
    else:
        status = PASS
        detail = f"{len(ratios)} colored markings checked"
    checks.append(
        GateCheck(
            "cmf.marking_contrast",
            "cmf",
            status,
            measured=min(ratios.values(), default=None),
            limit=MIN_MARKING_CONTRAST,
            detail=detail,
        )
    )
    return checks


def _content_checks(contract: UXContract) -> list[GateCheck]:
    feedback = {f.id: f for f in contract.feedback}
    covered = {a.feedback for a in contract.content if a.modality == feedback[a.feedback].modality}
    uncovered = sorted(set(feedback) - covered)
    checks = [
        GateCheck(
            "content.feedback_coverage",
            "content",
            FAIL if uncovered else PASS,
            measured=float(len(covered)),
            limit=float(len(feedback)),
            detail=(
                f"feedback without a content asset: {', '.join(uncovered)}"
                if uncovered
                else f"{len(feedback)} feedback records realized"
            ),
        )
    ]
    mismatched = sorted(
        f"{a.id}:{a.modality}!={feedback[a.feedback].modality}"
        for a in contract.content
        if a.modality != feedback[a.feedback].modality
    )
    checks.append(
        GateCheck(
            "content.modality_match",
            "content",
            FAIL if mismatched else PASS,
            detail=f"asset/feedback modality mismatch: {', '.join(mismatched)}"
            if mismatched
            else "",
        )
    )
    imported = {ref.path: set(ref.extracted) for ref in contract.imports if ref.system == "bard"}
    unlinked = sorted(
        f"{a.id}:{a.source.ref}#{a.source.cue}"
        for a in contract.content
        if a.source.kind == "bard_cue"
        and f"cue:{a.source.cue}" not in imported.get(a.source.ref, set())
    )
    bard_assets = [a for a in contract.content if a.source.kind == "bard_cue"]
    checks.append(
        GateCheck(
            "content.bard_cue_imported",
            "content",
            FAIL if unlinked else PASS,
            measured=float(len(bard_assets) - len(unlinked)),
            limit=float(len(bard_assets)),
            detail=(
                "bard cues not in an imported cue manifest (run `ux import --from bard`): "
                + ", ".join(unlinked)
                if unlinked
                else f"{len(bard_assets)} bard cues linked"
            ),
        )
    )
    return checks
