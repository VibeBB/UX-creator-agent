# ADR-0014: HIG numeric gates and structural projections

- Status: Accepted
- Date: 2026-09-28
- Related: ADR-0013 (projections), ADR-0005 (gates stay deterministic)

## Context

Touch-target size and color contrast are objective, measurable rules
(HIG 44pt, WCAG 2.x 4.5:1 / 3:1) but lived only as advisory review
notes. And three structural views — mindmap, sequence, WBS — had data
in the contract but no projection.

## Decision

- `controls:` contract list (`id`, `surface`, `kind`, `size_mm`,
  `fg`/`bg`, `large_text`, `touchpoint`) with fail-closed validators —
  a control on an unknown surface or touchpoint is a contract error.
- `hig.*` gate group: `hig.target_size` fails when a *sized* control of
  a physical-ish kind (button/touch/dial/switch) is under 7.8 mm
  (44pt @163ppi); `hig.contrast` applies WCAG relative luminance —
  4.5:1, or 3:1 when `large_text`. Unsized/uncolored controls are
  ignored, not assumed.
- Three deterministic projections: `mindmap.mmd` (contract overview),
  `{journey}.sequence.puml` (actor × surfaces per stage), `wbs.puml`
  (surface → touchpoint/control decomposition + implementation spec).

## Consequences

- Contract authors must declare what they measured; gates ignore what
  is absent rather than fabricating it.
- Example smart-kettle gained `boil_button` (14×14 mm) and
  `app_boil_tap` (9×9 mm, #FFFFFF on #0057D9 = 6.2:1) — both pass.
- WBS/sequence/mindmap render through the existing `render_all` glob;
  verified on the locked image.
