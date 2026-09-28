---
description: Plan and track a product revision across every sibling agent (producer / orchestrator).
argument-hint: <product>.production.json [--workspace <dir>] [--liaison-dir <dir>]
allowed-tools:
  - terminal
  - file_editor
---

Delegate to the `ux-producer` agent. Edit only the authored
`<product>.production.json`; then run
`python -m ux_creator produce <plan> --out <dir> --workspace <ws> --liaison-dir <requests-dir>`.
The command exits 0 only when every `production.*` gate passes; a
missing liaison directory or contract is `unknown` and fails closed.
Report the current stage, next actions, open decisions, and blockers from
the generated `<product>.production-status.md`.
