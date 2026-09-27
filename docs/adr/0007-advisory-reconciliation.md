# ADR-0007: Advisory reconciliation (L2 findings vs deterministic truth)

- Status: Accepted
- Date: 2026-09-27

## Context

`ux-review` writes L2 visual records (`review-visual-*.advisory.json`).
Two gaps remained: nothing checked whether a vision finding agrees with
the contract/gates, and nothing measured review coverage (which rendered
images lack a record).

## Decision

`reconcile_findings` scores each ok-status visual finding against
deterministic truth:

- `unreachable_state`, `missing_touchpoint`, `broken_flow` map onto
  facts the contract already knows (state reachability gates, declared
  touchpoints + imported ids, transition table) → `corroborated` /
  `contradicted`.
- Purely visual categories (label collisions, illegibility, …) are
  `unverifiable` — honest, not silent.

`build_report(out_dir=...)` adds `lenses.review`: record counts,
malformed files, severity/reconciliation tallies, contradicted findings,
and rendered images lacking a record (same slug rule as the stop hook).

Why not gate on it: advisory output is model judgement — noisy by
design. Using it as a verdict input would let a hallucinated
"unreachable_state" fail a correct design. Reconciliation exists to
*catch* bad findings (a `contradicted` record means the reviewer must
re-look), not to grant them authority. The verdict stays the exclusive
product of `gates.py`.

## Consequences

- `review-reconcile` CLI + `ux_review_reconcile` MCP tool are read-only
  and always `verdict: pass` unless they crash.
- Report gains a "Review lens (advisory)" markdown section;
  `ux-report.json` shape is additive.
