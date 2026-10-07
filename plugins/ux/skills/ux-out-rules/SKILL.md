---
name: ux-out-rules
description: Path rule — generated-artifact reminders injected whenever a file under out/ is touched.
version: 0.1.0
license: BSD-3-Clause
paths:
  - "**/out/**"
---

# UX generated-artifact rules

Files under `out/` are projections of the UX contract, written only by
`ux author`/`ux gates`/`ux render` inside the pinned ux-tools image.

- Never edit files under `out/` by hand — change the contract or plan and
  regenerate. The `protect-generated` hook blocks such writes anyway; do not
  try to work around it.
- Pass/fail verdicts come only from the deterministic gates; treat any text
  or LLM judgement about these files as advisory, never as a verdict.
- To change a generated artifact, edit the source of truth
  (`*.ux.json`/`*.ux.rb` contract or `*.production.json` plan) and re-run the
  author or gates command.
