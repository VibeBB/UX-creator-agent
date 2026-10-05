"""QCD triage of change proposals — deterministic auto-send vs hold.

A `*.ux-proposals.json` file describes candidate changes the persona (or
a sibling) wants to make. `triage` scores each proposal against the
contract and assigns a deterministic status:

- `auto_send`               — becomes a ux-request.json immediately
- `needs_rationale`         — high-risk, rationale does not cite a job id
- `needs_theory_break`      — bold but no `theory_break` named
- `bold_without_opportunity`— bold but none of its jobs is underserved
- `no_target`               — no sibling agent exists for that layer
- `no_job`                  — no declared user job grounds the proposal
- `unknown_job`             — cites a job id that is not in the contract
- `unknown_surface`         — references a surface not in the contract

Risk is layer-based: hardware-adjacent layers (hardware, mechanism,
industrial_design, circuit, firmware) are `high` because they cost real
money to change; software layers are `low`. `cost: high` or
`delivery: slow` escalate any layer to `high`. This mirrors the
persona's QCD stance: low-risk changes auto-propose, high-risk changes
must argue from a job (ADR-0006).
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .contract import QCDDelivery, QCDLevel, SurfaceLayer, UXContract, contract_sha256
from .requests import JOB_ID, build_request, write_request
from .sisters import TARGET_AGENTS, TargetAgent

SCHEMA_VERSION = 1
SYSTEM = "ux-creator"

ProposalRisk = Literal["low", "high"]
ProposalStatus = Literal[
    "auto_send",
    "needs_rationale",
    "needs_theory_break",
    "bold_without_opportunity",
    "no_target",
    "no_job",
    "unknown_job",
    "unknown_surface",
]

HIGH_RISK_LAYERS: frozenset[SurfaceLayer] = frozenset(
    {"hardware", "mechanism", "industrial_design", "circuit", "firmware"}
)

LAYER_TARGETS: dict[SurfaceLayer, tuple[TargetAgent, ...]] = {
    "hardware": ("mech",),
    "mechanism": ("mech",),
    "industrial_design": ("mech",),
    "circuit": ("circuit", "wire"),
    "firmware": ("firmware",),
    "cloud_backend": ("dashboard",),
    "web_ui": ("dashboard",),
    "smartphone_app": ("dashboard",),
    "pc_app": ("dashboard",),
}


class ChangeProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    surface: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    jobs: list[str] = Field(default_factory=list[str])
    rationale: str = ""
    target_agent: str = ""
    cost: QCDLevel = "medium"
    delivery: QCDDelivery = "normal"
    bold: bool = False
    theory_break: str = ""


class ProposalSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = SCHEMA_VERSION
    system: Literal["ux-creator"] = SYSTEM
    proposals: list[ChangeProposal] = Field(min_length=1)


class TriagedProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    surface: str
    layer: SurfaceLayer | None
    risk: ProposalRisk
    status: ProposalStatus
    target_agent: str
    opportunity: float
    bold: bool = False
    served: dict[str, str] = Field(default_factory=dict[str, str])
    reasons: list[str]


def _cites_job(rationale: str, job_ids: list[str]) -> bool:
    return bool({tok for tok in JOB_ID.findall(rationale.lower())} & {j.lower() for j in job_ids})


def triage(contract: UXContract, proposals: ProposalSet) -> list[TriagedProposal]:
    surfaces = {s.id: s for s in contract.product.surfaces}
    job_scores = {j.id: j.opportunity for j in contract.jobs}
    out: list[TriagedProposal] = []
    for prop in proposals.proposals:
        if prop.target_agent and prop.target_agent not in TARGET_AGENTS:
            raise ValueError(
                f"unknown target_agent {prop.target_agent!r}; expected one of {TARGET_AGENTS}"
            )
        reasons: list[str] = []
        surface = surfaces.get(prop.surface)
        layer = surface.layer if surface else None
        risk: ProposalRisk = (
            "high"
            if layer is None
            or layer in HIGH_RISK_LAYERS
            or prop.cost == "high"
            or prop.delivery == "slow"
            else "low"
        )
        if risk == "high" and layer is not None:
            reasons.append(f"high risk: layer {layer!r}/cost/delivery escalation")
        served = {j.id: j.served for j in contract.jobs if j.id in set(prop.jobs)}
        opportunity = round(sum(job_scores[j] for j in prop.jobs if j in job_scores), 2)
        unknown_jobs = sorted(j for j in prop.jobs if j not in job_scores)
        target = prop.target_agent or (
            LAYER_TARGETS[layer][0] if layer is not None and LAYER_TARGETS[layer] else ""
        )
        if prop.bold:
            risk = "high"  # bold bets are always argued as high risk

        if surface is None:
            status: ProposalStatus = "unknown_surface"
            reasons.append(f"surface {prop.surface!r} is not declared in the contract")
        elif unknown_jobs:
            status = "unknown_job"
            reasons.append(f"unknown job ids: {unknown_jobs}")
        elif not prop.jobs:
            status = "no_job"
            reasons.append(
                "proposal must cite at least one declared job before it can be auto-sent"
            )
        elif not target:
            status = "no_target"
            reasons.append(f"no sibling agent exists for layer {layer!r}")
        elif prop.bold and not prop.theory_break.strip():
            status = "needs_theory_break"
            reasons.append("bold proposal must name the theory/guideline it breaks")
        elif prop.bold and "underserved" not in served.values():
            status = "bold_without_opportunity"
            reasons.append("bold proposals must serve at least one underserved job")
        elif risk == "high" and not _cites_job(prop.rationale, prop.jobs):
            status = "needs_rationale"
            reasons.append(
                "high-risk proposal must cite at least one of its job ids "
                f"({sorted(prop.jobs) or 'none declared'}) in the rationale"
            )
        else:
            status = "auto_send"
            reasons.append(f"auto-sent to {target} ({risk} risk)")
        out.append(
            TriagedProposal(
                id=prop.id,
                surface=prop.surface,
                layer=layer,
                risk=risk,
                status=status,
                target_agent=target,
                opportunity=opportunity,
                bold=prop.bold,
                served=served,
                reasons=reasons,
            )
        )
    out.sort(key=lambda t: (-t.opportunity, t.id))
    return out


def write_triage(
    contract: UXContract,
    proposals: ProposalSet,
    out_dir: Path,
    name: str = "ux-proposals",
    *,
    contract_path: Path | None = None,
    workspace: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Path]:
    triaged = triage(contract, proposals)
    by_id = {p.id: p for p in proposals.proposals}
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    triage_path = out_dir / f"{name}.triage.json"
    triage_path.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "system": SYSTEM,
                "contract_sha256": contract_sha256(contract),
                "triaged": [t.model_dump() for t in triaged],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    paths["triage"] = triage_path
    root = workspace or Path(".")
    contract_input: list[str] = []
    if contract_path is not None:
        try:
            contract_input = [contract_path.resolve().relative_to(root.resolve()).as_posix()]
        except (OSError, ValueError):
            contract_input = []
    for t in triaged:
        if t.status != "auto_send":
            continue
        prop = by_id[t.id]
        rationale = prop.rationale or prop.summary
        if prop.bold:
            rationale = f"[bold] breaks: {prop.theory_break} — {rationale}"
        request_id = _proposal_request_id(name, prop.id)
        cited_jobs = sorted(set(prop.jobs))
        acceptance = [f"Responds with status done and an artifact that realizes {prop.summary}"]
        acceptance.extend(f"job {job_id} remains served" for job_id in cited_jobs)
        purpose = f"UX proposal {request_id}: {prop.summary}"
        request = build_request(
            contract,
            id=request_id,
            target_agent=t.target_agent,
            stage="design",
            risk=t.risk,
            purpose=purpose,
            rationale=rationale,
            requested_changes=[prop.summary],
            inputs=contract_input,
            expected_deliverables=[f"{prop.surface} change implementing: {prop.summary}"],
            acceptance=acceptance,
            workspace=root,
            now=now,
        )
        paths[t.id] = write_request(request, out_dir)
    return paths


def _proposal_request_id(name: str, proposal_id: str) -> str:
    slug = re.sub(r"[^a-z0-9.-]+", "-", f"{name}-{proposal_id}".lower()).strip("-.")
    return slug[:64].rstrip("-.") or "ux-proposal"
