# ADR-0008: Sister-agent response contract

- Status: Accepted
- Date: 2026-09-27

## Context

ux-creator emits `*.ux-request.json` change requests for its sisters
(ADR-0003), but the loop never closed: nothing told the persona whether
mech accepted the enclosure change or circuit rejected the LED duty.
Silence is indistinguishable from refusal, which stalls the design
conversation.

## Decision

A sister answers by writing `<request-stem>.ux-response.json` beside the
request: `{schema_version, system, request, responder, status, reason,
artifacts[]}` with `status ∈ {accepted, rejected, deferred, needs_info}`
and `responder` validated against `TARGET_AGENTS`.

`liaison_status` reconciles a directory deterministically: every request
is `open`, `answered`, or `mismatched` (response from the wrong agent);
responses with no matching request are `orphans`; unparseable files are
`malformed` — listed, never raised. Multiple responses per request:
latest sorted path wins.

Why informational only: a sister's rejection is design *signal* — the
persona must re-open the proposal with a better rationale or reframe the
job — never a gate input. `ux-report.json` gains `lenses.liaison` with
counts plus `rejected_high_risk` (the list the liaison agent should act
on first). Verdict stays gate-only.

## Consequences

- `ux liaison` CLI + `ux_liaison_status` MCP read tool; the e2e driver
  copies committed example responses into `out/` so the lens is
  exercised end-to-end.
- Requests and responses are looked up in the same directory — the one
  `write_triage` writes requests into.
