---
name: ux-contract-rules
description: Path rule — contract schema and provenance reminders injected whenever a *.ux.json or *.ux.rb file is touched.
version: 0.1.0
license: BSD-3-Clause
paths:
  - "**/*.ux.json"
  - "**/*.ux.rb"
---

# UX contract file rules

- `*.ux.json` follows the contract schema in `src/ux_creator/contract.py`
  (`schema_version: 1`, `system: "ux-creator"`; the canonical sample is
  `examples/smart-kettle/smart-kettle.ux.json`). Check the contract summary
  in `skills/ux-workflow/SKILL.md` before editing.
- `*.ux.rb` is the Ruby DSL source the contract is re-derived from via
  `from-ruby` — never post-edit the generated `*.ux.json`; fix the DSL and
  recompile inside the ux-tools image.
- Keep ids stable (personas, jobs, journeys, statecharts, controls) —
  gates, proposals, and SLP v2 requests cite them. High-risk proposals must
  cite a declared job id.
- `imports` entries bind each sister source path to SHA-256 provenance;
  claims read off images are advisory observations, never authored facts.
- Generated projections (`out/**` diagrams and exports, `manifest.json`,
  `provenance.json`, `ux-report.*`, `*.triage.json`, `*.production-status.*`)
  are never hand-edited — change the contract or plan and re-run the
  deterministic pipeline; gates stay fail-closed.
