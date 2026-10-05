---
name: ux-workflow
description: Execute a conversational UX design workflow with deterministic verification — contract, gates, projections, advisory review.
version: 0.1.0
license: BSD-3-Clause
triggers:
  - ux design
  - user experience
  - UX設計
  - ユーザー体験
  - ux-creator
---

# UX workflow

1. **Reframe** — never take the request literally. Decompose it into
   functional/emotional/social jobs (see `ux-jtbd`).
2. **Contract** — author `<project>.ux.json` (schema_version 1,
   system "ux-creator"). The contract is truth; everything else is a
   projection. The Ruby DSL (`ruby/bin/ux-dsl`) is the preferred authoring
   surface; compile with `python -m ux_creator from-ruby file.ux.rb --out
   <project>.ux.json`.
3. **Gates** — `python -m ux_creator gates <contract>` must report
   verdict pass. `unknown` fails the design (fail-closed).
4. **Projections** — `python -m ux_creator author <contract> --out
   out/<name> --render` writes Mermaid/PlantUML/XState/SCXML/stories/ODI
   projections plus manifest.json, provenance.json, ux-report.json/md.
   Rendered images need a `review-visual-*.advisory.json` record before
   finishing (`python -m ux_creator review-record`), then
   `review-reconcile` checks findings against the gates — contradicted
   findings must be re-examined, never used to override a verdict.
5. **Cooperation** — sibling artifacts are imported with sha256
   provenance (`ux import`); outgoing change requests use
   `ux request` (see `ux-sibling-cooperation`).

Rules that bind every step:

- Pass/fail verdicts come only from the deterministic gates. LLM and
  vision output is L2 advisory, never promoted.
- Generated projections are never edited by hand — the protect-generated
  hook blocks such writes; regenerate from the contract.
- Missing tools (mmdc, java/plantuml, ruby, mrbc) report `unknown` in
  renders/probes; they never crash the pipeline.

## Records you must leave

Use `ux_record_decision` for consequential choices and `ux_record_impression`
after each completed stage. Cover intake, research (personas and jobs),
journey, statechart, CMF, content, review, liaison, and production. Record
decisions such as the primary persona, job framing or ODI threshold, journey
stage cut, statechart guard or feedback channel, CMF material or finish,
sister-request risk class, workstream owner, and whether to accept or reject
a sister response. Impressions must describe what you noticed, what works,
what worries you, how a maker or user would read it, and what to do next in
at least 400 characters and three distinct sentences. After actually viewing
an image, add `ux_record_vision_review` bound to its path or source event.
