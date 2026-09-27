# ADR-0010: Bold proposals and the innovation lens

- Status: Accepted
- Date: 2026-09-27

## Context

The persona's mandate includes deliberately breaking guidelines when an
underserved job demands it ("Think Different"), but triage treated every
proposal alike — a button-removal and a copy tweak got the same path.
ODI scores existed but the underserved/overserved classification was
only prose in the ux-jtbd skill.

## Decision

- `Job.served` computes the classification deterministically
  (opportunity ≥ 15 underserved, ≤ 10 overserved) and is surfaced in
  `*.odi.csv` and `lenses.innovation.by_served`.
- `ChangeProposal` gains `bold`/`theory_break`. Triage blocks bold
  proposals lacking a named theory (`needs_theory_break`) or serving no
  underserved job (`bold_without_opportunity`) — the constraint is
  mechanical, not a judgement call: bold bets must aim where users are
  underserved, and must name the rule they break so the sister agent
  and reviewer can evaluate intent. Passing bold proposals are always
  `risk: high` and their ux-request rationale is prefixed
  `[bold] breaks: <theory_break> — `.
- **opportunity.coverage gate: deliberately omitted.** The spec called
  for a gate forcing underserved jobs to be covered by journeys — but
  no contract element references job ids (journeys link personas,
  loops/feedback link events/touchpoints). Adding a field would change
  the contract shape beyond the additive scope; inventing a linkage
  would gate on nothing. Skipped per the "don't invent a field" rule —
  the `lenses.innovation` section surfaces underserved jobs instead.

## Consequences

- The smart-kettle example intentionally contains a bold proposal
  (`no_button_boil`) that lands `bold_without_opportunity` — the kettle
  has no underserved job, which is exactly the honest deterministic
  answer.
- All changes additive; `schema_version` stays 1.
