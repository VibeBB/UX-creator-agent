# ADR-0015: Producer plan, CMF, and interaction content

- Status: Accepted
- Date: 2026-09-28
- Related: ADR-0003 (sibling contracts), ADR-0005 (feedback records),
  ADR-0008 (ux-response), ADR-0014 (contrast math); bard ADR-0011
  (product sound cues)

## Context

VibeBB's loop is describe → design/verify → build/try → feed measurements
back. Each sibling agent owns its domain contract, but nothing owned the
product as a whole: which agent does what, in which order, what is
blocked, and whether evaluation evidence reached the next revision.
Manufacturers call that role a producer or program manager; game and
animation studios call it production. Two further studio roles were
missing: industrial design / CMF (how the object looks and feels) and
interaction content (what the LED, buzzer, and app actually play).
ux-creator already owns surfaces (including `industrial_design`) and
multimodal `feedback[]`, so all three roles live here.

## Decision

- **Production plan.** A separate authored file
  `<product>.production.json` (`artifact_kind: ux_production_plan`) —
  not part of the UX contract, because it spans every sibling.
  Workstreams carry `stage` (requirements, design,
  manufacturing_handoff, build, evaluation, revision), `owner` (ux,
  wire, mech, circuit, bard, doc, simulation, production-engineering,
  firmware, user), `deliverable`, `depends_on`, `status`, `artifacts`,
  and an optional `request` stem linking a `ux-request.json`. Decisions,
  blockers, and evidence are first-class. Referential integrity is a
  schema error.
- **Production gates** (`production.*`, fail closed): acyclic
  dependencies; no dependency on a later stage; nothing started before
  its dependencies are done; `blocked` iff an open blocker/decision
  holds it; `done` only with artifacts on disk; `done` with a `request`
  only after an accepted, correctly-addressed ux-response (no liaison
  dir → `unknown`); evidence must cite an existing source and feed a
  design or revision workstream, and a done evaluation needs evidence;
  a linked UX contract must pass its gates once a `ux` workstream is
  done. `produce` exits 0 only on pass.
- **Status projections** (`production.mmd`,
  `production-status.{json,md}`) report current stage, next actions,
  blocked work, and open decisions with `authority: none`.
- **CMF.** Optional contract `cmf` block (form language, keywords,
  references, palette with roles, materials, finishes, per-surface parts,
  markings). Gates: every hardware/mechanism/industrial_design surface
  has a part; the palette has a primary; colored markings reach 3:1
  against their surface's part colors (WCAG non-text contrast), else a
  marking on an uncovered surface is `unknown`. Appearance judgement
  stays advisory. Projection: `<name>.cmf.md`.
- **Interaction content.** Optional contract `content[]`, one asset per
  feedback record, source `bard_cue` (audio, bard `cues.json` + cue id),
  `file`, or `inline` spec. Gates: every feedback has an asset of its
  modality; no modality mismatch; every bard cue resolves to a
  `cue:<id>` in an imported bard manifest (the import's sha256 is
  already pinned by `imports.*`). Projection: `<name>.content.json`.
- **Sound stays in bard.** ux-creator never composes melodies. It
  requests cues from bard, bard renders MIDI/MML with provenance, and
  `ux import --from bard` reads the cue manifest.

## Consequences

- New fields are optional; existing contracts, gate reports, and
  projections are unchanged. The Ruby DSL does not emit `cmf`/`content`
  yet — author them in the JSON contract.
- Firmware and bench evaluation have no dedicated agent; the plan names
  them as `firmware` / `user` owners until they do.
- The protect-generated hook covers the new projections; the authored
  `*.production.json` stays editable.
- `examples/smart-kettle-product/` exercises all three roles end to end
  with real bard output.
