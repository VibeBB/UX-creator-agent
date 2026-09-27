# ADR-0013: Service-blueprint and emotion-curve projections

- Status: Accepted
- Date: 2026-09-28

## Context

`service_blueprint` (frontstage/backstage/support) and per-stage
`emotion` existed in the contract since the scaffold but had no
projection — the data was invisible in `out/`.

## Decision

Two deterministic text projections in `write_projections`:

- `{name}.blueprint.puml` — PlantUML activity swimlanes (`|Customer|`
  shows each `journey.stage` with its touchpoints, then `|Frontstage|`,
  `|Backstage|`, `|Support|`). Emitted only when `service_blueprint`
  is declared; items are sanitized (`;` → `,`, newlines → space) so
  free text cannot break the syntax.
- `{name}.{journey}.emotion.mmd` — Mermaid `xychart-beta` line chart of
  stage emotion, plus `{name}.{journey}.emotion.json` data for tooling.

`xychart-beta` is still beta syntax in Mermaid — accepted because the
renderer is pinned by the locked `ux-tools` image (mermaid ≥10.6);
renders are verified in-image each e2e run. If the image's mermaid ever
drops it, the gate is the e2e render, not a silent skip.

## Consequences

- `manifest.json`/`provenance.json` pick up the new files for free.
- `protect_generated` gained `.emotion.json` to cover the new suffix.
- Emotion data is journaled twice (mmd + json): the mmd renders, the
  json feeds downstream tooling without parsing Mermaid.
