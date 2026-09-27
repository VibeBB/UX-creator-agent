# ADR-0012: Intake touchpoint candidates

- Status: Accepted
- Date: 2026-09-27
- Related: ADR-0007 (advisory reconciliation)

## Context

The reviewer sees real product photos and screenshots; the contract sees
only declared `stage.touchpoints`. Neither could talk to the other: a
photo showing a temperature dial the journey never mentions went
unrecorded, and a declared touchpoint no image confirms went unnoticed.

## Decision

A second advisory record type: `intake-touchpoints-<slug>.advisory.json`
(`tool: ux.intake_touchpoints`, `stage: intake`) carrying
`TouchpointCandidate`s — `{id (normalized), surface?, evidence,
confidence}` — written by `ux intake-record` and parsed fail-closed by
`parse_intake_record` (status ok requires ≥1 candidate with a
normalizable id).

`reconcile_intake` diffs observed vs declared, deterministically:
`declared`, `undeclared` (image-only candidates — routed to
`ux propose`, never hand-edited into the contract), `unobserved`
(contract-only), `surface_mismatch` (image's surface guess vs the
stage's declared surfaces), `malformed`. `lenses.review.intake`
surfaces the counts in the report; the verdict stays gate-only
(ADR-0007).

## Consequences

- No committed example record: the JSON's `image_sha256` would pretend
  provenance for an image that does not exist in the repo. Tests
  generate a 1×1 PNG instead; e2e copies any committed intake records
  when present (records: 0 today).
- Undeclared candidates feed the proposals pipeline (phase 4+) rather
  than mutating truth directly — observed ≠ declared, deliberately.
