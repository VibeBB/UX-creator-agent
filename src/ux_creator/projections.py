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
        lines.append(f"    section {stage.id}")
        task = touchpoints.replace(":", "-")
        if stage.jobs:
            task += f" (jobs {', '.join(stage.jobs)})"
        persona = (journey.persona or "user").replace(":", "-")
        lines.append(f"        {task}: {stage.emotion}: {persona}")
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
        if not journey_hits and not any(
            tp
            for j in contract.journeys
            for stage in j.stages
            if surface.id in stage.surfaces
            for tp in stage.touchpoints
        ):
            lines.append("    .")
        for stage_id in journey_hits:
            lines.append(f'    "{stage_id}"')
        lines.append("  }")
        lines.append("}")
    lines += ["}", "@endsalt"]
    return "\n".join(lines) + "\n"


def _puml_item(text: str) -> str:
    """One-line PlantUML activity text: `;` -> `,`, newlines -> space."""
    return text.replace(";", ",").replace("\n", " ").strip()


def _plantuml_blueprint(contract: UXContract) -> str:
    assert contract.service_blueprint is not None
    lines = [
        "@startuml",
        f"title {contract.product.name} — service blueprint",
        "|Customer|",
    ]
    if contract.journeys:
        for journey in contract.journeys:
            for stage in journey.stages:
                tps = ", ".join(_puml_item(tp) for tp in stage.touchpoints)
                label = f"{journey.id}/{stage.id}"
                lines.append(f":{label} — touchpoints {tps};")
    else:
        lines.append(":no journeys declared;")
    lanes = {
        "Frontstage": contract.service_blueprint.frontstage,
        "Backstage": contract.service_blueprint.backstage,
        "Support": contract.service_blueprint.support_processes,
    }
    for lane, items in lanes.items():
        lines.append(f"|{lane}|")
        for item in items:
            lines.append(f":{_puml_item(item)};")
    lines.append("@enduml")
    return "\n".join(lines) + "\n"


def _mermaid_emotion(journey: Journey) -> str:
    stages = ", ".join(f'"{stage.id}"' for stage in journey.stages)
    values = ", ".join(str(stage.emotion) for stage in journey.stages)
    return (
        "xychart-beta\n"
        f'    title "{journey.id} — emotion curve"\n'
        f"    x-axis [{stages}]\n"
        '    y-axis "emotion (1-5)" 1 --> 5\n'
        f"    line [{values}]\n"
    )


def _emotion_data(journey: Journey) -> str:
    rows = [
        {
            "stage": stage.id,
            "emotion": stage.emotion,
            "pain_points": stage.pain_points,
            "jobs": stage.jobs,
        }
        for stage in journey.stages
    ]
    return json.dumps(rows, indent=2, sort_keys=True) + "\n"


def _mm_label(text: str) -> str:
    """Mindmap-safe node text: ()/[] -> -, whitespace collapsed."""
    return text.replace("(", "-").replace(")", "-").replace("[", "-").replace("]", "-")


def _mermaid_mindmap(contract: UXContract) -> str:
    lines = ["mindmap", f"  root(({_mm_label(contract.product.name)}))", "    Personas"]
    for persona in contract.personas:
        lines.append(f"      {_mm_label(persona.id)}")
    lines.append("    Jobs")
    for job in contract.jobs:
        lines.append(f"      {_mm_label(job.id)} -{_mm_label(job.served)}-")
    lines.append("    Surfaces")
    for surface in contract.product.surfaces:
        lines.append(f"      {_mm_label(surface.id)}")
        touchpoints = sorted(
            {
                tp
                for journey in contract.journeys
                for stage in journey.stages
                if surface.id in stage.surfaces
                for tp in stage.touchpoints
            }
        )
        for tp in touchpoints:
            lines.append(f"        {_mm_label(tp)}")
    lines.append("    Journeys")
    for journey in contract.journeys:
        lines.append(f"      {_mm_label(journey.id)}")
        for stage in journey.stages:
            lines.append(f"        {_mm_label(stage.id)}")
    return "\n".join(lines) + "\n"


def _puml_text(text: str) -> str:
    return text.replace(":", "-").replace("\n", " ").strip()


def _plantuml_sequence(contract: UXContract, journey: Journey) -> str:
    surfaces: list[str] = []
    for stage in journey.stages:
        for sid in stage.surfaces:
            if sid not in surfaces:
                surfaces.append(sid)
    lines = [
        "@startuml",
        f"title {journey.id} — sequence",
        f'actor "{_puml_text(journey.persona or "user")}" as U',
    ]
    for i, sid in enumerate(surfaces):
        lines.append(f'participant "{sid}" as S_{i}')
    if not surfaces:
        lines.append('participant "unassigned" as S_0')
    for stage in journey.stages:
        lines.append(f"== {stage.id} ({stage.kind}) ==")
        for sid in stage.surfaces or ["unassigned"]:
            alias = f"S_{surfaces.index(sid)}" if sid in surfaces else "S_0"
            lines.append(f"U -> {alias} : {_puml_text(', '.join(stage.touchpoints) or '-')}")
        note = f"emotion {stage.emotion}/5"
        if stage.pain_points:
            note += " — pain: " + _puml_text(", ".join(stage.pain_points))
        lines.append(f"note right of U : {note}")
    lines.append("@enduml")
    return "\n".join(lines) + "\n"


def _plantuml_wbs(contract: UXContract) -> str:
    lines = ["@startwbs", f"* {_puml_text(contract.product.name)}"]
    surface_touchpoints: dict[str, set[str]] = {}
    for journey in contract.journeys:
        for stage in journey.stages:
            for sid in stage.surfaces:
                surface_touchpoints.setdefault(sid, set()).update(stage.touchpoints)
    for surface in contract.product.surfaces:
        lines.append(f"** {surface.id} ({surface.layer})")
        for tp in sorted(surface_touchpoints.get(surface.id, set())):
            lines.append(f"*** {_puml_text(tp)}")
        for control in contract.controls:
            if control.surface == surface.id:
                lines.append(f"*** control: {control.id}")
    if contract.implementation_spec:
        lines.append("** Implementation spec")
        for item in contract.implementation_spec:
            lines.append(f"*** {_puml_text(item)}")
    lines.append("@endwbs")
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


def _cmf_sheet(contract: UXContract) -> str:
    cmf = contract.cmf
    if cmf is None:
        return ""
    colors = {c.id: c for c in cmf.palette}
    materials = {m.id: m for m in cmf.materials}
    finishes = {f.id: f for f in cmf.finishes}
    surfaces = {s.id: s for s in contract.product.surfaces}
    lines = [
        f"# {contract.product.name} — CMF sheet",
        "",
        f"Form language: {cmf.form_language}",
    ]
    if cmf.keywords:
        lines.append(f"Keywords: {', '.join(cmf.keywords)}")
    lines += ["", "## Palette", "", "| Color | Role | Hex |", "| --- | --- | --- |"]
    lines += [f"| {c.name or c.id} (`{c.id}`) | {c.role} | `{c.hex}` |" for c in cmf.palette]
    lines += [
        "",
        "## Parts",
        "",
        "| Part | Surface | Color | Material | Finish |",
        "| --- | --- | --- | --- | --- |",
    ]
    for part in cmf.parts:
        surface = surfaces[part.surface]
        color = colors[part.color]
        material = materials[part.material]
        process = f" ({material.process})" if material.process else ""
        finish = finishes.get(part.finish)
        finish_text = "—"
        if finish is not None:
            texture = f", {finish.texture}" if finish.texture else ""
            finish_text = f"{finish.name} ({finish.gloss}{texture})"
        lines.append(
            f"| `{part.id}` | {surface.name or surface.id} ({surface.layer}) | "
            f"{color.name or color.id} `{color.hex}` | {material.name}{process} | {finish_text} |"
        )
    if cmf.markings:
        lines += [
            "",
            "## Markings",
            "",
            "| Marking | Surface | Kind | Content | Method | Color |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for m in cmf.markings:
            color_text = f"`{colors[m.color].hex}`" if m.color else "—"
            lines.append(
                f"| `{m.id}` | {m.surface} | {m.kind} | {m.content} | {m.method} | {color_text} |"
            )
    if cmf.references:
        lines += ["", "## References", ""]
        lines += [f"- {ref}" for ref in cmf.references]
    lines += [
        "",
        "Appearance review is advisory; only the `cmf.*` gates are verdicts.",
    ]
    return "\n".join(lines) + "\n"


def _content_map(contract: UXContract) -> dict[str, object]:
    """Feedback → content assets, ordered by feedback id, for firmware and app teams."""
    by_feedback: dict[str, list[dict[str, object]]] = {}
    for asset in sorted(contract.content, key=lambda a: a.id):
        entry: dict[str, object] = {
            "id": asset.id,
            "modality": asset.modality,
            "source": asset.source.model_dump(),
            "duration_ms": asset.duration_ms,
            "loop": asset.loop,
        }
        by_feedback.setdefault(asset.feedback, []).append(entry)
    feedback = [
        {
            "id": f.id,
            "trigger": f.trigger,
            "surface": f.surface,
            "modality": f.modality,
            "latency_ms": f.latency_ms,
            "assets": by_feedback.get(f.id, []),
        }
        for f in sorted(contract.feedback, key=lambda f: f.id)
    ]
    return {
        "schema_version": 1,
        "system": "ux-creator",
        "artifact_kind": "ux_content_map",
        "authority": "none",
        "product": contract.product.name,
        "feedback": feedback,
    }


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
    if contract.service_blueprint is not None:
        artifacts[f"{name}.blueprint.puml"] = _plantuml_blueprint(contract)
    artifacts[f"{name}.mindmap.mmd"] = _mermaid_mindmap(contract)
    artifacts[f"{name}.wbs.puml"] = _plantuml_wbs(contract)
    for journey in contract.journeys:
        artifacts[f"{name}.{journey.id}.sequence.puml"] = _plantuml_sequence(contract, journey)
    for journey in contract.journeys:
        artifacts[f"{name}.{journey.id}.emotion.mmd"] = _mermaid_emotion(journey)
        artifacts[f"{name}.{journey.id}.emotion.json"] = _emotion_data(journey)
    artifacts[f"{name}.stories.json"] = (
        json.dumps(_stories(contract), indent=2, sort_keys=True) + "\n"
    )
    artifacts[f"{name}.odi.csv"] = _odi_csv(contract)
    if contract.loops:
        artifacts[f"{name}.experience-loops.mmd"] = _mermaid_loops(contract)
    if contract.cmf is not None:
        artifacts[f"{name}.cmf.md"] = _cmf_sheet(contract)
    if contract.content:
        artifacts[f"{name}.content.json"] = (
            json.dumps(_content_map(contract), indent=2, sort_keys=True) + "\n"
        )

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
