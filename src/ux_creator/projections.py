"""Deterministic projections of the UXContract.

Mermaid journey/stateDiagram, PlantUML state/Salt wireframe, XState v5
machine JSON, SCXML, Storybook story requirements, the ODI opportunity
table, manifest.json and provenance.json. Nothing here judges the design.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from .contract import Journey, Statechart, UXContract, contract_sha256


def _mermaid_journey(contract: UXContract, journey: Journey) -> str:
    lines = ["journey", f"    title {journey.id} — {contract.product.name}"]
    for stage in journey.stages:
        touchpoints = ", ".join(stage.touchpoints) if stage.touchpoints else "-"
        lines.append(f"    section {stage.id}")
        lines.append(f"        {touchpoints}: {stage.emotion}: {journey.persona or 'user'}")
    return "\n".join(lines) + "\n"


def _mermaid_statechart(chart: Statechart) -> str:
    lines = ["stateDiagram-v2", f'    state "{chart.id}" as {chart.id}']
    for s in chart.states:
        if s.initial:
            lines.append(f"    [*] --> {s.id}")
        if s.final:
            lines.append(f"    {s.id} --> [*]")
    for t in chart.transitions:
        lines.append(f"    {t.from_state} --> {t.to} : {t.event}")
    return "\n".join(lines) + "\n"


def _plantuml_statechart(chart: Statechart) -> str:
    lines = ["@startuml", f"title {chart.id}"]
    for s in chart.states:
        if s.initial:
            lines.append(f"[*] --> {s.id}")
        if s.final:
            lines.append(f"{s.id} --> [*]")
    for t in chart.transitions:
        lines.append(f"{t.from_state} --> {t.to} : {t.event}")
    lines.append("@enduml")
    return "\n".join(lines) + "\n"


def _plantuml_wireframe(contract: UXContract) -> str:
    lines = ["@startsalt", f"title {contract.product.name} — wireframe skeleton", "{"]
    for surface in contract.product.surfaces:
        label = surface.name or surface.id
        lines += ["{+", f"  {label} ({surface.layer})", "  {"]
        journey_hits = sorted(
            {
                stage.id
                for j in contract.journeys
                for stage in j.stages
                if surface.id in stage.surfaces or stage.id in surface.id
            }
        )
        for tp in sorted(
            {
                tp
                for j in contract.journeys
                for stage in j.stages
                if surface.id in stage.surfaces
                for tp in stage.touchpoints
            }
        ):
            lines.append(f"    [ ] {tp}")
        for stage_id in journey_hits:
            lines.append(f'    "{stage_id}"')
        lines.append("  }")
    lines += ["}", "@endsalt"]
    return "\n".join(lines) + "\n"


def _xstate_machine(chart: Statechart) -> dict[str, Any]:
    initial = next((s.id for s in chart.states if s.initial), None)
    states: dict[str, Any] = {}
    for s in chart.states:
        on: dict[str, str] = {}
        for t in chart.transitions:
            if t.from_state == s.id:
                on[t.event] = t.to
        node: dict[str, Any] = {}
        if on:
            node["on"] = on
        if s.final:
            node["type"] = "final"
        states[s.id] = node
    machine: dict[str, Any] = {"id": chart.id, "states": states}
    if initial is not None:
        machine["initial"] = initial
    return machine


def _scxml(chart: Statechart) -> str:
    initial = next((s.id for s in chart.states if s.initial), "")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<scxml xmlns="http://www.w3.org/2005/07/scxml" version="1.0"'
        f' initial="{escape(initial)}" datamodel="python">',
    ]
    for s in chart.states:
        tag = "final" if s.final else "state"
        transitions = [] if s.final else [t for t in chart.transitions if t.from_state == s.id]
        if transitions:
            lines.append(f'  <{tag} id="{escape(s.id)}">')
            for t in transitions:
                lines.append(f'    <transition event="{escape(t.event)}" target="{escape(t.to)}"/>')
            lines.append(f"  </{tag}>")
        else:
            lines.append(f'  <{tag} id="{escape(s.id)}"/>')
    lines.append("</scxml>")
    return "\n".join(lines) + "\n"


def _stories(contract: UXContract) -> dict[str, Any]:
    stories: list[dict[str, Any]] = []
    for surface in contract.product.surfaces:
        title = f"{contract.product.name}/{surface.id}"
        stories.append(
            {
                "title": title,
                "surface": surface.id,
                "layer": surface.layer,
                "required_stories": [
                    "default",
                    "empty-state",
                    "error",
                    "loading"
                    if surface.layer in ("web_ui", "smartphone_app", "pc_app")
                    else "idle",
                ],
                "touchpoints": sorted(
                    {
                        tp
                        for j in contract.journeys
                        for st in j.stages
                        if surface.id in st.surfaces
                        for tp in st.touchpoints
                    }
                ),
            }
        )
    return {"schema_version": 1, "system": "ux-creator", "stories": stories}


def _odi_csv(contract: UXContract) -> str:
    rows = ["job_id,functional,emotional,social,importance,satisfaction,opportunity"]
    for job in sorted(contract.jobs, key=lambda j: (-j.opportunity, j.id)):
        fields = [
            job.id,
            job.functional,
            job.emotional,
            job.social,
            str(job.importance),
            str(job.satisfaction),
            f"{job.opportunity:.1f}",
        ]
        rows.append(",".join(f'"{f}"' if "," in f else f for f in fields))
    return "\n".join(rows) + "\n"


def write_projections(contract: UXContract, name: str, out_dir: Path) -> dict[str, Path]:
    """Write every projection; returns {artifact_name: path}."""
    out_dir.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, str] = {}
    for journey in contract.journeys:
        artifacts[f"{name}.{journey.id}.journey.mmd"] = _mermaid_journey(contract, journey)
    for chart in contract.statecharts:
        artifacts[f"{name}.{chart.id}.statechart.mmd"] = _mermaid_statechart(chart)
        artifacts[f"{name}.{chart.id}.statechart.puml"] = _plantuml_statechart(chart)
        artifacts[f"{name}.{chart.id}.xstate.json"] = (
            json.dumps(_xstate_machine(chart), indent=2, sort_keys=True) + "\n"
        )
        artifacts[f"{name}.{chart.id}.scxml"] = _scxml(chart)
    artifacts[f"{name}.wireframe.puml"] = _plantuml_wireframe(contract)
    artifacts[f"{name}.stories.json"] = (
        json.dumps(_stories(contract), indent=2, sort_keys=True) + "\n"
    )
    artifacts[f"{name}.odi.csv"] = _odi_csv(contract)

    paths: dict[str, Path] = {}
    for filename, text in artifacts.items():
        path = out_dir / filename
        path.write_text(text, encoding="utf-8")
        paths[filename] = path

    manifest = {
        "schema_version": 1,
        "artifacts": [
            {"path": fn, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for fn, p in sorted(paths.items())
        ],
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    paths["manifest.json"] = manifest_path
    return paths


def write_provenance(contract: UXContract, paths: dict[str, Path], out_dir: Path) -> Path:
    provenance = {
        "schema_version": 1,
        "system": "ux-creator",
        "authority": "none",
        "contract_sha256": contract_sha256(contract),
        "artifacts": {
            fn: hashlib.sha256(p.read_bytes()).hexdigest() for fn, p in sorted(paths.items())
        },
        "imports": [ref.model_dump() for ref in contract.imports],
    }
    path = out_dir / "provenance.json"
    path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
