# UX authoring workflow

The workflow makes the reasoning and evidence visible from initial brief to
handoff. Work can be conversational, but the current contract and project
files—not chat history—remain the durable workspace state.

## 1. Understand the brief

Start with the outcome, the people involved, their context, constraints, and
what is already known. `ux-research` helps separate functional, emotional,
and social Jobs-to-be-Done and score opportunity. Record uncertainty instead
of silently filling gaps with assumptions.

## 2. Author the UX contract

Create `{product}.ux.json` or compile an authored `*.ux.rb` into that JSON.
Include the product surfaces, personas, jobs, journeys, stage touchpoints,
service blueprint, statecharts, feedback, experience loops, quality/cost/
delivery stance, and any relevant CMF or interaction content.

Keep the contract authored and reviewable. Projections are regenerated from
it; do not edit projections as a substitute for changing the source model.

## 3. Run deterministic gates

Use `gates` while iterating and `author` when you want the projections and
report. Resolve `fail` findings. Treat `unknown` as unresolved: a missing
tool, file, measurement, or required field cannot be interpreted as success.
The gates cover declared contract properties, not unmodeled product risks.

## 4. Review the projections

Generate the diagrams, state machine exports, content/CMF sheets, and report.
When suitable previews are available, ask `ux-review` for image-bound
observations. Review the returned advisory record and reconcile it with
deterministic contract/gate evidence. A vision observation does not produce
or change a gate verdict.

For user-provided images, `intake-attachments` and the intake tools can record
touchpoint candidates. Reconcile those candidates against declared journey
touchpoints; add or resolve mismatches deliberately.

## 5. Capture decisions and stage impressions

At meaningful design stages, append a decision with alternatives, chosen
option, first principles, risks, revisit condition, and at least one bound
evidence item. At stage completion, append a long-form impression tied to
the artifacts that stage produced. The impression policy requires at least
400 characters and three sentences; include what was noticed, what works,
what worries you, how a maker or user may read it, and what to do next.

Use explicit vision-review records for image observations. These records are
append-only and do not substitute for authored changes or gates.

## 6. Coordinate with sister teams

Write one SLP v2 request per unit of work. State its purpose, stage, owner,
risk, requested changes, hashed inputs, expected deliverables, acceptance
criteria, and dependencies. High-risk requests must cite a declared job ID.
Use the task-tool brief to delegate to the registered sister liaison agent.

After a response arrives, reconcile its status, input hashes, artifact hashes,
gate evidence, event references, dependencies, and user questions. An
`answered` response does not mean every other request or production gate has
passed.

## 7. Plan build and evaluation

For product-level coordination, author `{product}.production.json`. Use
workstreams for requirements, design, manufacturing handoff, build,
evaluation, and revision; link dependencies and requests; record open
decisions and blockers; and feed evaluation evidence into a design or
revision workstream. Generate the status report and resolve production gate
failures before handoff.

## 8. Stop with a useful record

Before closing a meaningful design session, make sure the required VRP
records exist, unresolved issues are visible, and generated files are current.
The stop hook can ask for missing evidence; it does not silently create
design decisions. The latest hook result is summarized by `ux_records_status`.

## Completion checklist

- The authored contract validates and all applicable deterministic gates pass.
- Every unresolved `unknown`, assumption, risk, and user question is visible.
- Review and intake observations are reconciled with their source artifacts.
- Decisions and stage impressions cite current, hash-bound artifacts.
- Sister requests have valid responses or are explicitly open/blocked.
- Production status and evidence reflect the current revision.
- Reports and projections were regenerated from the authored source.

For the protocol details, see [Contracts](contracts.md),
[Sister cooperation](sister-cooperation.md), and
[Records and vision](records-and-vision.md).
