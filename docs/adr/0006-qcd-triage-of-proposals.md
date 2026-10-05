# ADR-0006: QCD triage of change proposals

- Status: Accepted
- Date: 2026-09-27

## Context

The persona's working rule — "low-risk changes auto-propose, high-risk
changes are argued with rationale" — was only half implemented:
`ux request` could write a single request, but nothing decided *whether*
a proposal should become a request. The plan calls for automatic
branching on evaluation results (低リスクは自動送信、高リスクは根拠要求).

## Decision

`proposals.py` scores a `*.ux-proposals.json` batch deterministically:

- **Risk is layer-based.** hardware, mechanism, industrial_design,
  circuit, and firmware layers are `high` because changing them costs
  tooling/board/firmware money; software layers are `low`.
  `cost: high` or `delivery: slow` escalate any layer — QCD is the
  stance, not a suggestion.
- **Fail-closed on the unknown.** A proposal naming an undeclared
  surface is `unknown_surface` with `risk: high` and produces no
  request; unknown job ids report `unknown_job`. Guessing a target for
  something the contract doesn't describe is worse than holding it.
- **Ground every request in a job.** Proposals without a declared job
  link are `no_job` and produce no request; low-risk does not mean
  ungrounded in a user outcome.
- **Only `auto_send` writes files.** `needs_rationale` (high-risk with
  no job id cited) and `no_target` (no sibling agent for that layer)
  produce triage records but no ux-request — the file list is exactly
  the deliverable set.
- Layer→agent defaults map to existing siblings (mech, circuit, wire);
  unserved layers get `""` rather than a fabricated target.
  `target_agent` may be overridden but is validated against
  `TARGET_AGENTS`.

## Consequences

- Ordering by ODI opportunity makes the triage file readable top-down:
  highest-opportunity changes first.
- No gate was added — proposals are outputs of the design loop, not
  contract inputs; verdict stays with `gates.py`.
