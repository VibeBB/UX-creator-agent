---
name: ux-diagrams
description: Projection formats emitted by ux-creator — Mermaid journey/state, PlantUML state + Salt wireframe, XState v5, SCXML, Storybook story requirements, and how Figma fits.
version: 0.1.0
license: BSD-3-Clause
triggers:
  - mermaid
  - plantuml
  - xstate
  - scxml
  - storybook
  - wireframe
  - figma
  - 図
  - ワイヤーフレーム
---

# Diagram projections

All projections are deterministic outputs of the contract — regenerate,
never hand-edit.

| File | Format | Producer |
| --- | --- | --- |
| `<name>.<journey>.journey.mmd` | Mermaid `journey` customer-journey map | `ux author` |
| `<name>.<chart>.statechart.mmd` | Mermaid `stateDiagram-v2` | `ux author` |
| `<name>.<chart>.statechart.puml` | PlantUML state diagram | `ux author` |
| `<name>.wireframe.puml` | PlantUML Salt wireframe skeleton from surfaces + touchpoints | `ux author` |
| `<name>.<chart>.xstate.json` | XState v5 machine (id/initial/states/on/final) | `ux author` |
| `<name>.<chart>.scxml` | SCXML document | `ux author` |
| `<name>.stories.json` | Storybook story requirements per surface (default/empty/error/loading-or-idle + touchpoints) | `ux author` |
| `<name>.odi.csv` | ODI opportunity table sorted by score | `ux author` |

Rendering runs `--render` inside the pinned ux-tools image: `mmdc` for
Mermaid, `java -jar $PLANTUML_JAR` (PlantUML MIT build) for PlantUML.
Missing tools record `unknown` in ux-report.json — never a crash.

## Figma, Overflow, Storybook

Figma and Overflow are proprietary SaaS and stay outside the image;
Storybook is a frontend-repo asset. ux-creator ships **requirements to
them** (`.stories.json`, XState, SCXML), not integrations. A designer
imports `.xstate.json` into Figma/Stately or `.stories.json` into the
frontend repo.
