"""UX report assembly: ux-report.json plus a human-readable summary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contract import UXContract
from .gates import GateReport
from .render import RenderResult


def build_report(
    contract: UXContract,
    gate_report: GateReport,
    renders: list[RenderResult] | None = None,
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
    report = build_report(contract, gate_report, renders)
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
    lines += ["", "## Checks", ""]
    for check in report["checks"]:
        detail = f" — {check['detail']}" if check.get("detail") else ""
        lines.append(f"- [{check['status']}] `{check['id']}`{detail}")
    lines.append("")
    return "\n".join(lines)
