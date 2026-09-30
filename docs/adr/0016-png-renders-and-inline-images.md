# ADR-0016: PNG renders and inline image observations

- Status: Accepted
- Date: 2026-09-29
- Related: ADR-0007 (advisory reconciliation), ADR-0015 (UX authoring)

## Context

The renderer produced SVG-only artifacts. SVG markup can expose labels to a
model as text, but it does not deliver the rendered picture to a
vision-capable model. Reviewers therefore could not reliably inspect the
visual state that the generated projections represented.

## Decision

- Render every Mermaid and PlantUML projection as both SVG and PNG. Mermaid
  keeps a transparent SVG background and uses a white PNG background; PNGs
  use scale 2 when supported by the pinned tools image. Keep `RenderResult`
  unchanged.
- Return each successful PNG inline from `ux_render` and
  `ux_author(render=true)` with its path and SHA-256. Attach at most eight
  images per tool result and skip inline attachment above 4 MiB.
- Record actual PNG observations from `ux_render`, `ux_author`, and
  `file_editor` views. An SVG and PNG sharing a stem are covered by one
  `review-visual` record.

## Consequences

- Authoring and rendering invoke the SVG and PNG renderers, so the render
  work is doubled.
- Tool results are bounded to eight inline images and 4 MiB per image; skipped
  images remain visible in the JSON metadata.
- Visual reviews and image observations remain L2 advisory data. They do not
  change deterministic gates or verdicts.
