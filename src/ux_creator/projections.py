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

from .contract import Journey, Statechart, Transition, UXContract, contract_sha256
from .gates import stage_job_coverage


def _mermaid_journey(contract: UXContract, journey: Journey) -> str:
    lines = ["journey", f"    title {journey.id} — {contract.product.name}"]
    for stage in journey.stages:
        touchpoints = ", ".join(stage.touchpoints) if stage.touchpoints else "-"
        label = stage.id
        if stage.jobs:
            label += f" [jobs: {', '.join(stage.jobs)}]"
        lines.append(f"    section {label}")
        lines.append(f"        {touchpoints}: {stage.emotion}: {journey.persona or 'user'}")
    return "\n".join(lines) + "\n"


def _transition_label(t: Transition) -> str:
    label = t.event
    if t.guard:
        label += f" [{t.guard}]"
    if t.actions:
        label += f" / {', '.join(t.actions)}"
    return label


def _mermaid_statechart(chart: Statechart) -> str:
    lines = ["stateDiagram-v2", f'    state "{chart.id}" as {chart.id}']
    for s in chart.states:
        if s.initial:
            lines.append(f"    [*] --> {s.id}")
        if s.final:
            lines.append(f"    {s.id} --> [*]")
    for t in chart.transitions:
        lines.append(f"    {t.from_state} --> {t.to} : {_transition_label(t)}")
    return "\n".join(lines) + "\n"


def _plantuml_statechart(chart: Statechart) -> str:
    lines = ["@startuml", f"title {chart.id}"]
    for s in chart.states:
        if s.initial:
            lines.append(f"[*] --> {s.id}")
        if s.final:
            lines.append(f"{s.id} --> [*]")
    for t in chart.transitions:
        lines.append(f"{t.from_state} --> {t.to} : {_transition_label(t)}")
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
        on: dict[str, Any] = {}
        grouped: dict[str, list[Any]] = {}
        for t in chart.transitions:
            if t.from_state == s.id:
                grouped.setdefault(t.event, []).append(t)
        for event, transitions in grouped.items():
            if len(transitions) == 1 and not transitions[0].guard and not transitions[0].actions:
                on[event] = transitions[0].to
            else:
                entries: list[dict[str, Any]] = []
                for t in transitions:
                    entry: dict[str, Any] = {"target": t.to}
                    if t.guard:
                        entry["guard"] = t.guard
                    if t.actions:
                        entry["actions"] = t.actions
                    entries.append(entry)
                on[event] = entries
        node: dict[str, Any] = {}
        if on:
            node["on"] = on
        if s.final:
            node["type"] = "final"
        if s.description:
            node["description"] = s.description
        if s.entry:
            node["entry"] = s.entry
        if s.exit:
            node["exit"] = s.exit
        if s.surface:
            node["meta"] = {"surface": s.surface}
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
        body: list[str] = []
        for phase, names in (("onentry", s.entry), ("onexit", s.exit)):
            if names:
                body.append(f"    <{phase}>")
                body += [f'      <log label="action" expr="\'{escape(a)}\'"/>' for a in names]
                body.append(f"    </{phase}>")
        for t in transitions:
            attrs = f'event="{escape(t.event)}" target="{escape(t.to)}"'
            if t.guard:
                attrs += f' cond="{escape(t.guard)}"'
            if t.actions:
                body.append(f"    <transition {attrs}>")
                body += [f'      <log label="action" expr="\'{escape(a)}\'"/>' for a in t.actions]
                body.append("    </transition>")
            else:
                body.append(f"    <transition {attrs}/>")
        if body:
            lines.append(f'  <{tag} id="{escape(s.id)}">')
            lines += body
            lines.append(f"  </{tag}>")
        else:
            lines.append(f'  <{tag} id="{escape(s.id)}"/>')
    lines.append("</scxml>")
    return "\n".join(lines) + "\n"


def _stories(contract: UXContract) -> dict[str, Any]:
    stories: list[dict[str, Any]] = []
    for surface in contract.product.surfaces:
        title = f"{contract.product.name}/{surface.id}"
        state_ids = sorted(
            {
                s.id
                for chart in contract.statecharts
                for s in chart.states
                if s.surface == surface.id
            }
        )
        required = [
            "default",
            "empty-state",
            "error",
            "loading" if surface.layer in ("web_ui", "smartphone_app", "pc_app") else "idle",
        ]
        required += state_ids
        feedback_ids = sorted(f.id for f in contract.feedback if f.surface == surface.id)
        stories.append(
            {
                "title": title,
                "surface": surface.id,
                "layer": surface.layer,
                "required_stories": sorted(set(required)),
                "states": state_ids,
                "feedback": feedback_ids,
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


def _mermaid_loops(contract: UXContract) -> str:
    lines = ["flowchart LR"]
    for loop in contract.loops:
        lines.append(f'    subgraph {loop.id} ["{loop.id} ({loop.cadence})"]')
        previous = f"{loop.id}_start"
        lines.append(f'        {previous}(["start"])')
        for i, step in enumerate(loop.steps):
            node = f"{loop.id}_{i}"
            lines.append(f'        {node}["{step}"]')
            lines.append(f"        {previous} --> {node}")
            previous = node
        reward = loop.reward or "reward"
        lines.append(f'        {loop.id}_reward[["{reward}"]]')
        lines.append(f"        {previous} --> {loop.id}_reward")
        lines.append("    end")
    if not contract.loops:
        lines.append('    empty["no experience loops"]')
    return "\n".join(lines) + "\n"


def _odi_csv(contract: UXContract) -> str:
    coverage = stage_job_coverage(contract)
    rows = [
        "job_id,functional,emotional,social,importance,satisfaction,opportunity,served,covered_by"
    ]
    for job in sorted(contract.jobs, key=lambda j: (-j.opportunity, j.id)):
        fields = [
            job.id,
            job.functional,
            job.emotional,
            job.social,
            str(job.importance),
            str(job.satisfaction),
            f"{job.opportunity:.1f}",
            job.served,
            "|".join(coverage.get(job.id, [])),
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
    if contract.loops:
        artifacts[f"{name}.experience-loops.mmd"] = _mermaid_loops(contract)

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
