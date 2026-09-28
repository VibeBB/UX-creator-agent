"""Product-level production plan — the producer / orchestrator view (ADR-0015).

A ``<product>.production.json`` plan spans every sibling agent and the whole
making loop: requirements → design → manufacturing handoff → build →
evaluation → revision. Workstreams carry an owner, a deliverable, the
workstreams they depend on, a status, and the artifacts that prove a
``done`` status. Decisions and blockers make stalls explicit; evidence
records carry build/evaluation observations back into design or revision.

``run_production_gates`` is deterministic and fail-closed. The status
projection (current stage, next actions, open decisions) is informational.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .contract import load_contract
from .gates import FAIL, PASS, UNKNOWN, CheckStatus, GateCheck, Verdict, run_gates
from .responses import liaison_status

ARTIFACT_KIND: Final = "ux_production_plan"
STATUS_KIND: Final = "ux_production_status"

ProductStage = Literal[
    "requirements", "design", "manufacturing_handoff", "build", "evaluation", "revision"
]
STAGES: tuple[ProductStage, ...] = (
    "requirements",
    "design",
    "manufacturing_handoff",
    "build",
    "evaluation",
    "revision",
)
Owner = Literal[
    "ux",
    "wire",
    "mech",
    "circuit",
    "bard",
    "doc",
    "simulation",
    "production-engineering",
    "firmware",
    "user",
]
WorkStatus = Literal["todo", "in_progress", "blocked", "done"]
_ID = r"^[a-z][a-z0-9_]{0,47}$"


class Workstream(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=_ID)
    stage: ProductStage
    owner: Owner
    deliverable: str = Field(min_length=1)
    depends_on: list[str] = Field(default_factory=list[str])
    status: WorkStatus = "todo"
    artifacts: list[str] = Field(default_factory=list[str])
    request: str = ""  # <stem> of a <stem>.ux-request.json in the liaison dir
    notes: str = ""


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=_ID)
    question: str = Field(min_length=1)
    options: list[str] = Field(default_factory=list[str])
    status: Literal["open", "decided"] = "open"
    decision: str = ""
    rationale: str = ""
    blocks: list[str] = Field(default_factory=list[str])


class Blocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=_ID)
    workstream: str = Field(min_length=1)
    description: str = Field(min_length=1)
    status: Literal["open", "resolved"] = "open"


class Evidence(BaseModel):
    """A build or evaluation observation fed into the next design iteration."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=_ID)
    workstream: str = Field(min_length=1)
    observation: str = Field(min_length=1)
    source: str = Field(min_length=1)  # workspace path of the measurement / log / photo
    feeds: list[str] = Field(min_length=1)


class ProductionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    system: Literal["ux-creator"] = "ux-creator"
    artifact_kind: Literal["ux_production_plan"] = ARTIFACT_KIND
    product: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    contract: str = ""  # workspace path of the product's .ux.json
    workstreams: list[Workstream] = Field(min_length=1)
    decisions: list[Decision] = Field(default_factory=list[Decision])
    blockers: list[Blocker] = Field(default_factory=list[Blocker])
    evidence: list[Evidence] = Field(default_factory=list[Evidence])

    @model_validator(mode="after")
    def _refs_known(self) -> ProductionPlan:
        for label, ids in (
            ("workstream", [w.id for w in self.workstreams]),
            ("decision", [d.id for d in self.decisions]),
            ("blocker", [b.id for b in self.blockers]),
            ("evidence", [e.id for e in self.evidence]),
        ):
            if len(ids) != len(set(ids)):
                dupes = sorted({i for i in ids if ids.count(i) > 1})
                raise ValueError(f"duplicate {label} ids: {dupes}")
        known = {w.id for w in self.workstreams}
        for w in self.workstreams:
            if w.id in w.depends_on:
                raise ValueError(f"workstream {w.id} depends on itself")
            unknown = sorted(set(w.depends_on) - known)
            if unknown:
                raise ValueError(f"workstream {w.id}: unknown dependencies {unknown}")
        for d in self.decisions:
            unknown = sorted(set(d.blocks) - known)
            if unknown:
                raise ValueError(f"decision {d.id}: blocks unknown workstreams {unknown}")
            if d.status == "decided" and not d.decision:
                raise ValueError(f"decision {d.id}: decided without a decision")
            if d.status == "open" and d.decision:
                raise ValueError(f"decision {d.id}: open but has a decision")
        for b in self.blockers:
            if b.workstream not in known:
                raise ValueError(f"blocker {b.id}: unknown workstream {b.workstream!r}")
        for e in self.evidence:
            unknown = sorted(({e.workstream} | set(e.feeds)) - known)
            if unknown:
                raise ValueError(f"evidence {e.id}: unknown workstreams {unknown}")
        return self

    def by_id(self) -> dict[str, Workstream]:
        return {w.id: w for w in self.workstreams}


def load_plan(path: Path | str) -> ProductionPlan:
    return ProductionPlan.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def plan_sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


@dataclass(frozen=True)
class ProductionReport:
    checks: list[GateCheck]
    verdict: Verdict

    def to_dict(self, plan: ProductionPlan, sha256: str) -> dict[str, object]:
        return {
            "schema_version": 1,
            "gate": "ux-creator.production",
            "plan": {"product": plan.product, "revision": plan.revision, "sha256": sha256},
            "verdict": self.verdict,
            "summary": {
                status: sum(1 for c in self.checks if c.status == status)
                for status in (PASS, FAIL, UNKNOWN)
            },
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


def _check(check_id: str, bad: list[str], label: str, ok: str = "") -> GateCheck:
    return GateCheck(
        check_id,
        "production",
        FAIL if bad else PASS,
        measured=float(len(bad)),
        limit=0.0,
        detail=f"{label}: {', '.join(bad)}" if bad else ok,
    )


def _cycle(plan: ProductionPlan) -> list[str]:
    deps = {w.id: list(w.depends_on) for w in plan.workstreams}
    state: dict[str, int] = {}
    path: list[str] = []

    def visit(node: str) -> list[str]:
        state[node] = 1
        path.append(node)
        for nxt in sorted(deps[node]):
            if state.get(nxt) == 1:
                return [*path[path.index(nxt) :], nxt]
            if nxt not in state:
                found = visit(nxt)
                if found:
                    return found
        path.pop()
        state[node] = 2
        return []

    for node in sorted(deps):
        if node not in state:
            found = visit(node)
            if found:
                return found
    return []


def _open_holds(plan: ProductionPlan) -> dict[str, list[str]]:
    holds: dict[str, list[str]] = {}
    for b in plan.blockers:
        if b.status == "open":
            holds.setdefault(b.workstream, []).append(f"blocker {b.id}")
    for d in plan.decisions:
        if d.status == "open":
            for wid in d.blocks:
                holds.setdefault(wid, []).append(f"decision {d.id}")
    return holds


def run_production_gates(
    plan: ProductionPlan, workspace: Path, liaison_dir: Path | None = None
) -> ProductionReport:
    ws = plan.by_id()
    rank = {stage: i for i, stage in enumerate(STAGES)}
    checks: list[GateCheck] = []

    cycle = _cycle(plan)
    checks.append(_check("production.acyclic", [" -> ".join(cycle)] if cycle else [], "cycle"))

    backwards = sorted(
        f"{w.id}({w.stage})<-{d}({ws[d].stage})"
        for w in plan.workstreams
        for d in w.depends_on
        if rank[ws[d].stage] > rank[w.stage]
    )
    checks.append(_check("production.stage_order", backwards, "depends on a later stage"))

    early = sorted(
        f"{w.id}:{w.status}<-{d}:{ws[d].status}"
        for w in plan.workstreams
        if w.status in ("in_progress", "done")
        for d in w.depends_on
        if ws[d].status != "done"
    )
    checks.append(_check("production.dependency_status", early, "started before dependencies"))

    holds = _open_holds(plan)
    unexplained = sorted(
        w.id for w in plan.workstreams if w.status == "blocked" and w.id not in holds
    )
    stale = sorted(
        f"{w.id}:{'+'.join(holds[w.id])}"
        for w in plan.workstreams
        if w.status == "done" and w.id in holds
    )
    checks.append(
        _check(
            "production.blockers_explained",
            [f"blocked without open blocker/decision: {u}" for u in unexplained]
            + [f"done with open holds: {s}" for s in stale],
            "inconsistent",
        )
    )

    no_evidence: list[str] = []
    missing: list[str] = []
    for w in plan.workstreams:
        if w.status != "done":
            continue
        if not w.artifacts:
            no_evidence.append(w.id)
        missing += [f"{w.id}:{a}" for a in w.artifacts if not (workspace / a).is_file()]
    checks.append(
        _check(
            "production.done_has_artifacts",
            [f"{i}: no artifacts" for i in no_evidence] + [f"{m}: missing" for m in missing],
            "done without artifact evidence",
        )
    )

    checks.append(_request_check(plan, liaison_dir))

    eval_done = [w.id for w in plan.workstreams if w.stage == "evaluation" and w.status == "done"]
    loop_bad = sorted(
        f"{e.id}->{f}"
        for e in plan.evidence
        for f in e.feeds
        if ws[f].stage not in ("design", "revision")
    )
    loop_bad += sorted(
        f"{e.id}:source {e.source} missing"
        for e in plan.evidence
        if not (workspace / e.source).is_file()
    )
    if eval_done and not plan.evidence:
        loop_bad.append(f"evaluation done ({', '.join(eval_done)}) without evidence")
    checks.append(_check("production.evidence_loop", loop_bad, "feedback loop broken"))

    if plan.contract:
        checks.append(_contract_check(plan, workspace))

    verdict: Verdict = PASS if all(c.status == PASS for c in checks) else FAIL
    return ProductionReport(checks=checks, verdict=verdict)


def _request_check(plan: ProductionPlan, liaison_dir: Path | None) -> GateCheck:
    linked = [w for w in plan.workstreams if w.request]
    if not linked:
        return GateCheck("production.requests_answered", "production", PASS, detail="no requests")
    if liaison_dir is None or not liaison_dir.is_dir():
        return GateCheck(
            "production.requests_answered",
            "production",
            UNKNOWN,
            detail="workstreams cite ux-requests but no liaison directory was given",
        )
    entries = {e.request: e for e in liaison_status(liaison_dir, liaison_dir).entries}
    bad: list[str] = []
    unknown: list[str] = []
    for w in linked:
        entry = entries.get(w.request)
        if entry is None:
            unknown.append(f"{w.id}:{w.request} not found")
        elif w.status == "done" and not (
            entry.state == "answered" and entry.response_status == "accepted"
        ):
            bad.append(f"{w.id}:{entry.state}/{entry.response_status or '-'}")
    status: CheckStatus = FAIL if bad else UNKNOWN if unknown else PASS
    detail = "; ".join(
        part
        for part in (
            f"done without an accepted response: {', '.join(bad)}" if bad else "",
            f"missing requests: {', '.join(unknown)}" if unknown else "",
        )
        if part
    )
    return GateCheck("production.requests_answered", "production", status, detail=detail)


def _contract_check(plan: ProductionPlan, workspace: Path) -> GateCheck:
    path = workspace / plan.contract
    if not path.is_file():
        return GateCheck(
            "production.ux_contract", plan.contract, UNKNOWN, detail="contract file missing"
        )
    try:
        contract = load_contract(path)
    except Exception as exc:
        return GateCheck("production.ux_contract", plan.contract, FAIL, detail=f"invalid: {exc}")
    report = run_gates(contract, workspace)
    failing = sorted(c.id for c in report.checks if c.status != PASS)
    ux_done = any(w.owner == "ux" and w.status == "done" for w in plan.workstreams)
    if report.verdict == PASS:
        return GateCheck("production.ux_contract", plan.contract, PASS, detail="ux gates pass")
    return GateCheck(
        "production.ux_contract",
        plan.contract,
        FAIL if ux_done else UNKNOWN,
        detail=f"ux gates not passing: {', '.join(failing)}",
    )


@dataclass(frozen=True)
class StageRow:
    stage: ProductStage
    state: str
    todo: int
    in_progress: int
    blocked: int
    done: int

    @property
    def total(self) -> int:
        return self.todo + self.in_progress + self.blocked + self.done


def stage_rows(plan: ProductionPlan) -> list[StageRow]:
    rows: list[StageRow] = []
    for stage in STAGES:
        items = [w for w in plan.workstreams if w.stage == stage]
        todo, active, blocked, done = (
            sum(1 for w in items if w.status == s)
            for s in ("todo", "in_progress", "blocked", "done")
        )
        if not items:
            state = "empty"
        elif done == len(items):
            state = "done"
        elif blocked:
            state = "blocked"
        elif active or done:
            state = "active"
        else:
            state = "pending"
        rows.append(StageRow(stage, state, todo, active, blocked, done))
    return rows


def production_status(plan: ProductionPlan, report: ProductionReport) -> dict[str, object]:
    ws = plan.by_id()
    holds = _open_holds(plan)
    rows = stage_rows(plan)
    current = next((r.stage for r in rows if r.state not in ("done", "empty")), "complete")
    stages = [
        {
            "stage": r.stage,
            "state": r.state,
            "workstreams": r.total,
            "todo": r.todo,
            "in_progress": r.in_progress,
            "blocked": r.blocked,
            "done": r.done,
        }
        for r in rows
    ]
    next_actions = [
        {"id": w.id, "owner": w.owner, "stage": w.stage, "deliverable": w.deliverable}
        for w in plan.workstreams
        if w.status == "todo"
        and w.id not in holds
        and all(ws[d].status == "done" for d in w.depends_on)
    ]
    return {
        "schema_version": 1,
        "system": "ux-creator",
        "artifact_kind": STATUS_KIND,
        "authority": "none",
        "product": plan.product,
        "revision": plan.revision,
        "goal": plan.goal,
        "verdict": report.verdict,
        "current_stage": current,
        "stages": stages,
        "next_actions": next_actions,
        "blocked": [
            {"id": wid, "holds": holds[wid]} for wid in sorted(holds) if ws[wid].status != "done"
        ],
        "open_decisions": [
            {"id": d.id, "question": d.question, "options": d.options, "blocks": d.blocks}
            for d in plan.decisions
            if d.status == "open"
        ],
        "evidence": [
            {"id": e.id, "from": e.workstream, "feeds": e.feeds, "observation": e.observation}
            for e in plan.evidence
        ],
        "failing_checks": [c.id for c in report.checks if c.status != PASS],
    }


_STATUS_CLASS = {"todo": "todo", "in_progress": "active", "blocked": "blocked", "done": "done"}


def _mermaid_plan(plan: ProductionPlan) -> str:
    lines = ["flowchart LR"]
    for stage in STAGES:
        items = [w for w in plan.workstreams if w.stage == stage]
        if not items:
            continue
        lines.append(f"  subgraph {stage}[{stage.replace('_', ' ')}]")
        lines += [
            f'    {w.id}["{w.id}<br/>{w.owner}: {w.status}"]:::{_STATUS_CLASS[w.status]}'
            for w in items
        ]
        lines.append("  end")
    for w in plan.workstreams:
        lines += [f"  {d} --> {w.id}" for d in w.depends_on]
    for e in plan.evidence:
        lines += [f"  {e.workstream} -. {e.id} .-> {f}" for f in e.feeds]
    lines += [
        "  classDef todo fill:#ffffff,stroke:#888888",
        "  classDef active fill:#dbeafe,stroke:#1d4ed8",
        "  classDef blocked fill:#fee2e2,stroke:#b91c1c",
        "  classDef done fill:#dcfce7,stroke:#15803d",
    ]
    return "\n".join(lines) + "\n"


def _status_markdown(status: dict[str, object], plan: ProductionPlan) -> str:
    lines = [
        f"# {plan.product} {plan.revision} — production status",
        "",
        f"Goal: {plan.goal}",
        "",
        f"Verdict: **{status['verdict']}** / current stage: **{status['current_stage']}**",
        "",
        "| Stage | State | Done | In progress | Blocked | To do |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    lines += [
        f"| {r.stage} | {r.state} | {r.done} | {r.in_progress} | {r.blocked} | {r.todo} |"
        for r in stage_rows(plan)
        if r.total
    ]
    lines += ["", "## Workstreams", "", "| Id | Stage | Owner | Status | Deliverable |"]
    lines.append("| --- | --- | --- | --- | --- |")
    lines += [
        f"| `{w.id}` | {w.stage} | {w.owner} | {w.status} | {w.deliverable} |"
        for w in plan.workstreams
    ]
    open_decisions = [d for d in plan.decisions if d.status == "open"]
    if open_decisions:
        lines += ["", "## Open decisions", ""]
        lines += [
            f"- `{d.id}`: {d.question}"
            + (f" (options: {', '.join(d.options)})" if d.options else "")
            for d in open_decisions
        ]
    open_blockers = [b for b in plan.blockers if b.status == "open"]
    if open_blockers:
        lines += ["", "## Open blockers", ""]
        lines += [f"- `{b.id}` on `{b.workstream}`: {b.description}" for b in open_blockers]
    if plan.evidence:
        lines += ["", "## Evidence fed back", ""]
        lines += [
            f"- `{e.id}` from `{e.workstream}` → {', '.join(e.feeds)}: {e.observation} ({e.source})"
            for e in plan.evidence
        ]
    lines += ["", "Status is a projection of the plan; only `production.*` checks are verdicts."]
    return "\n".join(lines) + "\n"


def write_production(
    plan: ProductionPlan,
    report: ProductionReport,
    name: str,
    out_dir: Path,
    plan_path: Path,
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    status = production_status(plan, report)
    sha = plan_sha256(plan_path)
    status["plan_sha256"] = sha
    status["report"] = report.to_dict(plan, sha)
    texts = {
        f"{name}.production.mmd": _mermaid_plan(plan),
        f"{name}.production-status.json": json.dumps(status, indent=2, sort_keys=True) + "\n",
        f"{name}.production-status.md": _status_markdown(status, plan),
    }
    paths: dict[str, Path] = {}
    for filename, text in texts.items():
        path = out_dir / filename
        path.write_text(text, encoding="utf-8")
        paths[filename] = path
    return paths
