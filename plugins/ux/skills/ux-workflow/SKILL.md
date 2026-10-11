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

## Records you must leave (VibeBB Record Protocol — mandatory, unprompted)

Record these without being asked; the Stop hook refuses to finish a
session that still owes them (see `docs/records-protocol.md`).

UX context: Use `ux_record_decision` for consequential choices and `ux_record_impression`
after each completed stage. Cover intake, research (personas and jobs),
journey, statechart, CMF, content, review, liaison, and production. Record
decisions such as the primary persona, job framing or ODI threshold, journey
stage cut, statechart guard or feedback channel, CMF material or finish,
sister-request risk class, workstream owner, and whether to accept or reject
a sister response. Impressions must describe what you noticed, what works,
what worries you, how a maker or user would read it, and what to do next in
at least 400 characters and three distinct sentences. After actually viewing
an image, add `ux_record_vision_review` bound to its path or source event.

- **Decision** (`ux_record_decision`) for every non-trivial choice:
  the question, the first principles / physical laws / standards it rests
  on, at least two options with pros and cons, the chosen option, a
  rationale of 200+ characters, evidence (artifact paths are hashed; cite
  datasheets or standards as references), assumptions, unknowns, residual
  risks and the observation that would reopen it. Reason from principles,
  not from habit.
- **Stage impression** (`ux_record_impression`) when a stage ends,
  after its final regeneration (VRP v2): 400+ characters and 3+
  sentences of prose plus `facets` — `observed` (2+ concrete things you
  saw), `works`, `concerns` (`id`, `text`, `severity`, `about` = the
  plugin that owns it or `self`, `anchor`), `feelings.maker` and
  `feelings.user`, `next_actions` — and 2+ `claims` whose `anchor` is an
  exact token in the cited artifact (state, stage, touchpoint id,
  persona, event); mention one anchor in the prose. Put testable ideas for any
  sister in `insights` (`hypothesis`, `proposed_change`,
  `expected_effect`, `test`, `target`). Set `confidence` and `unknowns`.
  List the stage's output files or directories so the impression is
  bound to their sha256. A near copy of an earlier impression is
  refused; when one reads similarly, add `delta`.
- **Sister impressions you took in**: imports log a read receipt
  automatically (`ux_record_read` for anything else). Answer each one
  in `upstream` (`system`, `event_id`, `disposition`
  adopted/deferred/disputed/noted, `effect` on your design, optional
  `concern_ids`). Only existing records are cited — never wait for one.
  A concern another sister disputed cannot come back while the artifacts
  are unchanged; change the design or bring new evidence.
- **Insight status** (`ux_record_insight`) when you try, adopt, reject
  or defer a hypothesis. Adopting needs a deterministic gate pass and the
  decision; a rejected insight returns only through `revisits`.
- **Vision review** (`ux_record_vision_review`) every time you look
  at an image (a rendered drawing, a photo, a screenshot, an
  `inspect_image_with_vision` answer): findings, the full impression
  body judging accuracy, ambiguity, design intent and whether the shop
  floor could act on it, and a `lookback` entry re-checking every claim
  against the image. Bind it to `image_path` or to the vision event's
  `source_event_id`. For the journey, statechart and wireframe PNGs
  (`dual_review_globs`) delegate one blind review with `task` to `ux-blind-review` (it never
  sees your review), then `ux_record_reconcile` both. A split allows
  exactly one `tiebreak` review and a second reconcile; a split after
  that is `unknown`, and nothing is re-asked.
- **Song receipt** (`ux_record_song_receipt`) for each bard song
  addressed to ux in `liaison/*.bard-song.json`: what it made you feel
  and whether it makes you look at the design again. Never ask bard for
  another song in reply.

Vision, impressions and songs are advisory: they never override a
deterministic gate verdict. Results do not have to be identical from run
to run; the reasoning must be recorded every run. The Stop hook refuses
at most twice, then lets the session end and leaves the gaps in
`records-status.json`. `ux_records_status` shows what is still owed;
`ux_records_search` and `ux_records_digest` show what every sister
thought.
