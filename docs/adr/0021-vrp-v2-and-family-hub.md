# ADR-0021: VRP v2 and the UX family hub

## Status

Accepted.

## Context

VRP v1 records were append-only but unchained, free-text only and
unanswerable: a sister could not tell whether its concern had been read,
a disputed concern could be raised again forever, and a single vision
review had no independent check. wire-agent shipped VRP v2 as the family
reference (`docs/records-protocol.md`).

## Decision

- Port VRP v2 unchanged: `src/ux_creator/_vrp.py` is a byte copy of the
  shared `_records.py`, `records.py` differs from wire's only in `PLUGIN`,
  and the shared hook hashes in `scripts/check_shared_hooks.py` follow the
  canonical copy.
- Add `ux-blind-review` with the `blind-guard` hook for journey,
  statechart and wireframe PNGs (`dual_review_globs`).
- Because UX is the hub that reads every sister, add `vrp_hub.hub()`
  (`ux_records_hub`, `ux record hub`): per-sister aggregation and
  elementary cycles in the "raiser -> owner" graph of open concerns and
  disputes. ECR/ECO chain cycles stay with the change check.

## Consequences

The hub view is advisory: `status` is `clear` or `attention`, never a
gate verdict. A broken sister log is listed and excluded, as in the
digest. `review-record` needs a `--vrp-json` body, so v1 call sites fail
closed instead of writing an unanswerable review.
Liaison reconciliation resolves a sister's `decision_refs` and
`impression_refs` only against an intact v2 chain: a log that fails
`verify_log` marks the response `broken` and contributes no event ids.
A sister still on VRP v1 (every record `schema_version: 1`) has no chain
to verify, so its ids resolve as before until its next v2 write archives
the log.
