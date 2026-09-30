"""UX report assembly: ux-report.json plus a human-readable summary."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast

from .advisory import (
    load_intake_records,
    load_visual_reviews,
    reconcile_findings,
    reconcile_intake,
)
from .contract import UXContract
from .gates import GateReport, stage_job_coverage
from .render import RenderResult
from .responses import liaison_status

_REVIEW_IMAGE_SUFFIXES = {".svg", ".png"}


def _review_slug(stem: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-") or "image"


def review_lens(contract: UXContract, gate_report: GateReport, out_dir: Path) -> dict[str, Any]:
    """Measured advisory-review coverage; informational only, never a verdict."""
    records, malformed = load_visual_reviews(out_dir)
    findings = reconcile_findings(contract, gate_report, records)
    by_severity: dict[str, int] = {"info": 0, "minor": 0, "major": 0}
    for f in findings:
        by_severity[f.severity] += 1
    reconciliation = {"corroborated": 0, "contradicted": 0, "unverifiable": 0}
    for f in findings:
        reconciliation[f.reconciliation] += 1
    reviewed = {
        _review_slug(path.stem.removeprefix("review-visual-").removesuffix(".advisory"))
        for path, _r in records
    }
    unreviewed_by_slug: dict[str, Path] = {}
    for image in sorted(out_dir.iterdir()):
        if not image.is_file() or image.suffix.lower() not in _REVIEW_IMAGE_SUFFIXES:
            continue
        slug = _review_slug(image.stem)
        if slug in reviewed or (out_dir / f"review-visual-{slug}.advisory.json").exists():
            continue
        existing = unreviewed_by_slug.get(slug)
        if existing is None or (
            image.suffix.lower() == ".png" and existing.suffix.lower() != ".png"
        ):
            unreviewed_by_slug[slug] = image
    images_without = sorted(str(image) for image in unreviewed_by_slug.values())
    intake_records, intake_malformed = load_intake_records(out_dir)
    intake = reconcile_intake(contract, intake_records)
    return {
        "records": sum(1 for _p, r in records if r.status == "ok"),
        "malformed": [str(p) for p in malformed],
        "findings_by_severity": by_severity,
        "reconciliation": reconciliation,
        "contradicted": [
            {"category": f.category, "where": f.where, "record": f.record}
            for f in findings
            if f.reconciliation == "contradicted"
        ],
        "images_without_record": images_without,
        "intake": {
            "records": sum(1 for _p, r in intake_records if r.status == "ok"),
            "declared_count": len(intake.declared),
            "undeclared": intake.undeclared,
            "unobserved": intake.unobserved,
            "surface_mismatch": intake.surface_mismatch,
            "malformed": [str(p) for p in intake_malformed],
        },
    }


def liaison_lens(out_dir: Path) -> dict[str, Any]:
    """Measured sister-agent response coverage; informational only."""
    status = liaison_status(out_dir, out_dir)
    by_status: dict[str, int] = {
        "accepted": 0,
        "rejected": 0,
        "deferred": 0,
        "needs_info": 0,
    }
    for entry in status.entries:
        if entry.response_status is not None:
            by_status[entry.response_status] += 1
    return {
        "requests": len(status.entries),
        "answered": sum(1 for e in status.entries if e.state == "answered"),
        "open": sum(1 for e in status.entries if e.state == "open"),
        "mismatched": sum(1 for e in status.entries if e.state == "mismatched"),
        "by_status": by_status,
        "rejected_high_risk": [
            e.request
            for e in status.entries
            if e.risk == "high" and e.response_status in ("rejected", "deferred")
        ],
        "orphans": status.orphans,
        "malformed": status.malformed,
    }


def innovation_lens(contract: UXContract, out_dir: Path) -> dict[str, Any]:
    """ODI classification + bold-proposal accounting; informational only."""
    by_served: dict[str, list[str]] = {
        "underserved": [],
        "appropriate": [],
        "overserved": [],
    }
    for job in contract.jobs:
        by_served[job.served].append(job.id)
    bold_proposals = 0
    bold_blocked: list[str] = []
    for triage_file in sorted(out_dir.glob("*.triage.json")):
        try:
            data = json.loads(triage_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for item in data.get("triaged", []):
            if not isinstance(item, dict):
                continue
            entry = cast(dict[str, Any], item)
            if not entry.get("bold"):
                continue
            bold_proposals += 1
            if entry.get("status") in ("needs_theory_break", "bold_without_opportunity"):
                bold_blocked.append(str(entry.get("id")))
    coverage = stage_job_coverage(contract)
    uncovered = [job_id for job_id in by_served["underserved"] if job_id not in coverage]
    return {
        "by_served": {k: sorted(v) for k, v in by_served.items()},
        "coverage": coverage,
        "uncovered_underserved": uncovered,
        "bold_proposals": bold_proposals,
        "bold_blocked": sorted(bold_blocked),
        "core_experience": contract.core_experience,
    }


def build_report(
    contract: UXContract,
    gate_report: GateReport,
    renders: list[RenderResult] | None = None,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    report = gate_report.to_dict(contract)
    report["schema_version"] = 1
    report["elements"] = {
        "personas": len(contract.personas),
        "jobs": len(contract.jobs),
        "journeys": len(contract.journeys),
        "stages": sum(len(j.stages) for j in contract.journeys),
        "statecharts": len(contract.statecharts),
        "surfaces": len(contract.product.surfaces),
        "top_opportunities": [
            {"id": j.id, "opportunity": j.opportunity}
            for j in sorted(contract.jobs, key=lambda j: (-j.opportunity, j.id))[:5]
        ],
    }
    report["imports"] = [ref.model_dump() for ref in contract.imports]
    modalities: dict[str, int] = {}
    for f in contract.feedback:
        modalities[f.modality] = modalities.get(f.modality, 0) + 1
    fed = {f.surface for f in contract.feedback}
    report["lenses"] = {
        "game_design": {
            "loops": len(contract.loops),
            "feedback_count": len(contract.feedback),
            "feedback_by_modality": dict(sorted(modalities.items())),
            "surfaces_without_feedback": sorted(
                s.id for s in contract.product.surfaces if s.id not in fed
            ),
            "avg_loop_length": round(
                sum(len(loop.steps) for loop in contract.loops) / max(len(contract.loops), 1),
                2,
            ),
            "onboard_stages": sum(
                1
                for journey in contract.journeys
                for stage in journey.stages
                if stage.kind == "onboard"
            ),
            "recover_stages": sum(
                1
                for journey in contract.journeys
                for stage in journey.stages
                if stage.kind == "recover"
            ),
        }
    }
    if out_dir is not None and out_dir.is_dir():
        report["lenses"]["review"] = review_lens(contract, gate_report, out_dir)
        report["lenses"]["liaison"] = liaison_lens(out_dir)
        report["lenses"]["innovation"] = innovation_lens(contract, out_dir)
    if renders is not None:
        report["renders"] = [
            {
                "source": str(r.source),
                "output": str(r.output) if r.output else None,
                "status": r.status,
                "detail": r.detail,
            }
            for r in renders
        ]
    return report


def write_report(
    contract: UXContract,
    gate_report: GateReport,
    out_dir: Path,
    renders: list[RenderResult] | None = None,
) -> Path:
    report = build_report(contract, gate_report, renders, out_dir=out_dir)
    path = out_dir / "ux-report.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "ux-report.md").write_text(render_markdown(report), encoding="utf-8")
    return path


def render_markdown(report: dict[str, Any]) -> str:
    design = report["design"]
    elements = report["elements"]
    lines = [
        f"# UX report: {design['name']}",
        "",
        f"**verdict: {report['verdict']}** (pass {report['summary']['pass']}, "
        f"fail {report['summary']['fail']}, unknown {report['summary']['unknown']})",
        "",
        "## Elements",
        "",
        f"- personas: {elements['personas']}",
        f"- jobs: {elements['jobs']}",
        f"- journeys: {elements['journeys']} ({elements['stages']} stages)",
        f"- statecharts: {elements['statecharts']}",
        f"- surfaces: {elements['surfaces']}",
        "",
        "## Top ODI opportunities",
        "",
    ]
    for opp in elements["top_opportunities"]:
        lines.append(f"- `{opp['id']}` — opportunity {opp['opportunity']}")
    lens = report.get("lenses", {}).get("game_design", {})
    if lens:
        lines += [
            "",
            "## Game-design lens",
            "",
            f"- experience loops: {lens['loops']} (avg length {lens['avg_loop_length']})",
            f"- feedback: {lens['feedback_count']} "
            f"({', '.join(f'{k}={v}' for k, v in lens['feedback_by_modality'].items()) or 'none'})",
            f"- surfaces without feedback: "
            f"{', '.join(lens['surfaces_without_feedback']) or 'none'}",
            f"- onboard stages: {lens['onboard_stages']}, recover stages: {lens['recover_stages']}",
        ]
    review = report.get("lenses", {}).get("review", {})
    if review:
        recon = review["reconciliation"]
        lines += [
            "",
            "## Review lens (advisory)",
            "",
            f"- advisory records: {review['records']} (malformed: {len(review['malformed'])})",
            f"- findings by severity: "
            f"{', '.join(f'{k}={v}' for k, v in review['findings_by_severity'].items())}",
            f"- reconciliation: corroborated={recon['corroborated']}, "
            f"contradicted={recon['contradicted']}, "
            f"unverifiable={recon['unverifiable']}",
            f"- images without a review record: {len(review['images_without_record'])}",
        ]
        intake = review.get("intake", {})
        if intake:
            lines.append(
                f"- intake records: {intake['records']} "
                f"(declared {intake['declared_count']}, "
                f"unobserved {len(intake['unobserved'])})"
            )
            if intake["undeclared"]:
                lines.append(
                    "  - candidate touchpoints — consider a proposal: "
                    + ", ".join(intake["undeclared"])
                )
            if intake["unobserved"]:
                lines.append("  - declared but never observed: " + ", ".join(intake["unobserved"]))
        for c in review["contradicted"]:
            lines.append(f"  - contradicted: `{c['category']}` at {c['where']} ({c['record']})")
    liaison = report.get("lenses", {}).get("liaison", {})
    if liaison:
        lines += [
            "",
            "## Liaison lens",
            "",
            f"- requests: {liaison['requests']} "
            f"(answered {liaison['answered']}, open {liaison['open']}, "
            f"mismatched {liaison['mismatched']})",
            f"- response statuses: "
            f"{', '.join(f'{k}={v}' for k, v in liaison['by_status'].items())}",
            f"- rejected/deferred high-risk requests: "
            f"{', '.join(liaison['rejected_high_risk']) or 'none'}",
            f"- orphan responses: {len(liaison['orphans'])}, "
            f"malformed files: {len(liaison['malformed'])}",
        ]
    innovation = report.get("lenses", {}).get("innovation", {})
    if innovation:
        served = innovation["by_served"]
        lines += [
            "",
            "## Innovation lens",
            "",
            f"- underserved jobs: {', '.join(served['underserved']) or 'none'}",
            f"- appropriate jobs: {', '.join(served['appropriate']) or 'none'}",
            f"- overserved jobs: {', '.join(served['overserved']) or 'none'}",
            f"- uncovered underserved jobs: "
            f"{', '.join(innovation['uncovered_underserved']) or 'none'}",
            f"- bold proposals: {innovation['bold_proposals']} "
            f"(blocked: {', '.join(innovation['bold_blocked']) or 'none'})",
            f"- core experience: {innovation['core_experience']}",
        ]
    lines += ["", "## Checks", ""]
    for check in report["checks"]:
        detail = f" — {check['detail']}" if check.get("detail") else ""
        lines.append(f"- [{check['status']}] `{check['id']}`{detail}")
    lines.append("")
    return "\n".join(lines)
