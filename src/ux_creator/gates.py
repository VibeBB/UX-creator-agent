"""Deterministic UX gates — the only pass/fail authority.

Every check emits a structured result: status is "pass", "fail", or
"unknown"; "unknown" and "fail" both make the design verdict fail
(fail-closed). Thresholds are never relaxed to reach a pass.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .contract import UXContract, contract_sha256

CheckStatus = Literal["pass", "fail", "unknown"]


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
    verdict: Literal["pass", "fail"]

    def to_dict(self, contract: UXContract) -> dict[str, Any]:
        summary = {
            "pass": sum(1 for c in self.checks if c.status == "pass"),
            "fail": sum(1 for c in self.checks if c.status == "fail"),
            "unknown": sum(1 for c in self.checks if c.status == "unknown"),
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


def _wrap(check_id: str, fn: Any, *args: Any) -> list[GateCheck]:
    try:
        return fn(*args)
    except Exception as exc:  # fail-closed: unexpected error → unknown
        return [GateCheck(check_id, check_id, "unknown", detail=f"check error: {exc}")]


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
                "pass" if len(initials) == 1 else "fail",
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
                "pass" if not undefined else "fail",
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
                "pass" if not unreachable else "fail",
                detail=f"unreachable: {', '.join(unreachable)}" if unreachable else "",
            )
        )
        finals = {s.id for s in chart.states if s.final}
        dead = sorted(s for s in state_ids - finals if not adjacency.get(s))
        checks.append(
            GateCheck(
                f"{cid}.no_dead_end",
                chart.id,
                "pass" if not dead else "fail",
                detail=f"non-final states with no exit: {', '.join(dead)}" if dead else "",
            )
        )
    if not contract.statecharts:
        checks.append(
            GateCheck("statechart.present", "statecharts", "fail", detail="no statecharts declared")
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
                "pass" if not missing else "fail",
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
                "pass" if not bare else "fail",
                detail=(
                    f"stages with emotion<=2 and no pain_point: {', '.join(bare)}" if bare else ""
                ),
            )
        )
    if not contract.journeys:
        checks.append(
            GateCheck("journey.present", "journeys", "fail", detail="no journeys declared")
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
            "pass" if contract.jobs and not thin else "fail",
            detail=(
                "no jobs declared"
                if not contract.jobs
                else (f"jobs missing dimensions: {', '.join(thin)}" if thin else "")
            ),
        )
    )
    return checks


def _core_experience_checks(contract: UXContract) -> list[GateCheck]:
    return [
        GateCheck(
            "core_experience.non_empty",
            "core_experience",
            "pass" if contract.core_experience.strip() else "fail",
        )
    ]


def _import_checks(contract: UXContract, workspace: Path) -> list[GateCheck]:
    checks: list[GateCheck] = []
    for ref in contract.imports:
        path = workspace / ref.path
        cid = f"imports.{ref.system}:{Path(ref.path).name}"
        if not path.is_file():
            checks.append(
                GateCheck(cid, ref.path, "unknown", detail="imported file missing in workspace")
            )
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        checks.append(
            GateCheck(
                cid,
                ref.path,
                "pass" if digest == ref.sha256 else "fail",
                detail=f"sha256 {digest[:12]}… vs declared {ref.sha256[:12]}…",
            )
        )
    return checks


def run_gates(contract: UXContract, workspace: Path | None = None) -> GateReport:
    checks: list[GateCheck] = []
    checks += _wrap("statechart", _statechart_checks, contract)
    checks += _wrap("journey", _journey_checks, contract)
    checks += _wrap("jobs", _job_checks, contract)
    checks += _wrap("core_experience", _core_experience_checks, contract)
    if contract.imports:
        checks += _wrap("imports", _import_checks, contract, workspace or Path.cwd())
    verdict: Literal["pass", "fail"] = "pass" if all(c.status == "pass" for c in checks) else "fail"
    return GateReport(checks=checks, verdict=verdict)
