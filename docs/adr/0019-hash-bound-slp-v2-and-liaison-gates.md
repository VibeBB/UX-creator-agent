# ADR-0019: Hash-bound SLP v2 and deterministic liaison reconciliation

- Status: Accepted
- Date: 2026-10-05

## Context

The original UX request/response file exchange named work but did not prove
which input files were used, whether sibling artifacts were still current, or
whether a completed request had recorded its decisions and stage impressions.
The initial liaison summary also covered only a subset of the VibeBB family.
Production plans need a fail-closed answer when requests are missing, stale,
or assigned to the wrong owner.

## Decision

- Use strict, frozen SLP v2 request and response models with
  `schema_version: 2` and `system: "ux-creator"`.
- Register the ten sister targets, their actual agent names, liaison agents,
  and expected inbox/respond tool names in `src/ux_creator/sisters.py`.
- Require normalized workspace-relative input and artifact paths and bind
  those files to SHA-256. Require timezone-aware timestamps and explicit
  high-risk job rationale.
- Do not replace a different request unless the caller explicitly requests
  replacement. Identical request writes remain idempotent.
- Reconcile request/response pairs as `open`, `answered`, `mismatched`,
  `stale`, `broken`, `blocked`, or `circular`. List malformed files and
  orphan responses separately; do not silently drop them.
- Keep ordinary liaison summaries informational, but use request completion,
  owner alignment, liaison integrity, and VRP event evidence as explicit
  production gates.
- Expose the same deterministic request, delegation, reconciliation, and
  production behavior through CLI and stdio MCP entry points.

## Consequences

- A response binds its input hashes, artifacts, gate verdicts, and VRP event
  references to the request. A changed input becomes stale rather than
  implicitly current.
- `answered` means the response is structurally and evidentially reconciled;
  its response status can still be rejected, deferred, or needs-info.
- Production plans that cite requests must include a matching target owner.
  A workstream marked done needs a done response and decision/impression
  references.
- The UX repository defines the producer-side protocol and registry. Sister
  inbox/respond implementations remain owned by their respective
  repositories and are not claimed as complete here.
- Legacy v1 requests/responses do not validate as v2. Examples and tests
  should be migrated together with protocol changes.

## Alternatives considered

- **Keep request files unhashed:** rejected because a response could be
  accepted after its inputs changed.
- **Treat every valid response as accepted work:** rejected because a valid
  rejection or needs-info response is still a reconciled conversation, not
  completed work.
- **Make every liaison problem a UX contract verdict:** rejected because
  ordinary coordination status is useful context; production-specific
  readiness checks belong to the production gate set.
- **Modify sister repositories in this change:** rejected because this
  repository's change scope is the UX producer and protocol implementation.

## Verification

The registry is tested against sister agent names; CLI and MCP exercise
request creation and delegation; fixtures cover all seven liaison states,
malformed/orphan files, stale hashes, and production projections. Checked-in
v2 examples are reconciled by the example coverage tests and
`scripts/e2e_authoring.py`.
