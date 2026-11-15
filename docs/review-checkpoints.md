# Bounded review collection

The coordinator uses `ux_review_checkpoint` or the launcher's
`review-checkpoint --json <request.json>` command to retain references to
completed image reviews across interruptions. Native OpenHands
`task_tool_set` executes every child; this collector never runs tasks or
stores conversation history. A collected record is advisory evidence,
never product acceptance, workflow completion, or Stop permission.

## Create and inspect

```json
{
  "action": "create",
  "checkpoint_id": "kettle-review",
  "session_id": "<native coordinator session ID>",
  "contract_path": "smart-kettle.ux.json",
  "sources": [{"image_path": "out/kettle/statechart.png", "checklist": "statechart"}]
}
```

Every action requires the same `checkpoint_id` and coordinator `session_id`.
If `OPENHANDS_SESSION_ID` is set, it must match. Paths are resolved within
the workspace. Each unique source creates primary and blind pairs. The
checkpoint lives at `observations/ux/review-checkpoints/<checkpoint_id>.json`
and binds the contract path/SHA, image path/SHA, checklist, role, attempt
count, at most two attempt-gap reasons and collected event IDs. Existing
checkpoints cannot be recreated. Retrying or collecting a later review
preserves earlier attempt-gap reasons.
Keep the same checkpoint and coordinator identity for the same review run;
creating another checkpoint is a separate scope, not an attempt-cap reset.

Use `status` to reload it without rewriting checkpoint bytes. Every load
rehashes the contract and images and verifies referenced VRP records,
native reviewer relationships and returned-image observations. Missing,
changed, mismatched or ambiguous evidence blocks reuse. The JSON seal
detects accidental edits; it is an integrity checksum, not authentication
against a writer who can replace files and recompute hashes.

## Act on one pair at a time

| Action | Additional inputs | Behavior |
| --- | --- | --- |
| `status` | None | Deterministic inspection; never consumes an attempt or rewrites the checkpoint. |
| `start` | None | Recovers intact records from stopped attempts, then reserves an eligible pair if needed. Primary precedes blind. |
| `collect` | `pair_id`, `review_event_id` | Accepts only the active pair's newly written, source/role/session/delivery-bound VRP record. |
| `pause` | `reason` | Retains an explicit provider, timeout, budget, cancellation, missing-image or interruption gap; attempts remain consumed. |
| `tiebreak` | An image's primary or blind `pair_id` | Adds one tiebreak pair only after an intact coordinator reconciliation records a round-1 disagreement. |

If `delegate` is non-null, pass its fields to native `task_tool_set`. Do not add
`resume` or send the work to an old child. Both reviewer definitions use
20 iterations and native budget 1.5. Wait for the child; task success alone
does not collect evidence. Submit the returned event ID with `collect`.
An old review predating the pair's first `start`, another role, another path, another
coordinator, or an unbound image delivery cannot complete the pair.

After a stopped child wrote its record but lost its final reply, pause with
the interruption reason and call `start` again. The collector revalidates
uncollected evidence from that pair's first reservation before spending
another attempt. A unique intact match is collected without a new attempt,
including after the second attempt; ambiguous matches fail closed. It may
then reserve the next pair, or return `collected` with `delegate: null`.
The original sequence boundary and all attempt-gap reasons survive retries.
Valid event-only reviews remain in the sequence history but cannot complete
an image-review pair; they do not block unrelated image collection.

Only one pair may be active in a checkpoint, with at most two fresh attempts
per image/checklist/role. A failed collection leaves the pair active until
the coordinator pauses it or provides valid evidence. A process lock and
atomic replacement serialize checkpoint writes. If the coordinator is
interrupted after `start`, the reservation survives. Check native child
status and wait for it to stop before pausing. `pause` neither cancels a task
nor asserts it stopped; no new plugin retry or cancellation mechanism exists.

Completed records are reused only within the same validated checkpoint.
They must still match the current image and contract SHA, reviewer role,
native coordinator relationship and unique image-delivery observation.
Image delivery establishes returned bytes, not model perception. Native
vision-inspector selection can still be unknown; see the
[image-delivery research](research/session-reassessment-2026-11-15/review-image-delivery.md).

Blind and tiebreak children receive the image/contract paths and hashes,
checklist, role and opaque primary event ID. They must not receive checkpoint
paths or previous review prose. The blind guard denies checkpoint CLI/MCP
access and record-file reads; the writer privately resolves the opaque ID.

After primary/blind collection, use `ux_record_reconcile` as coordinator.
A round-1 disagreement permits one tiebreak; reconcile again afterward.
The checkpoint retains that reconciliation's event ID and revalidates its
image, coordinator, round, metrics and computed disagreement on every load.
An unresolved second round stays unknown. `collected` only means every
requested pair has a valid record; reconciliation, deterministic gates and
product acceptance remain separate. The response always reports
`scope: review-record-collection` and `acceptance: unknown`.
