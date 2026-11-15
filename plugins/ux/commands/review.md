---
description: Advisory visual review of rendered UX artifacts.
argument-hint: <out_dir>
allowed-tools:
  - terminal
  - file_editor
  - task_tool_set
---

Collect reviews with `ux_review_checkpoint` (or the UX launcher's
`review-checkpoint --json <request.json>` CLI). Create one checkpoint naming
your native coordinator `session_id`, the contract path, and each image's
`image_path` and `checklist`. On return, use `status` with that same ID to
revalidate completed source/role pairs; never reset an existing checkpoint.
See [bounded review collection](../../../docs/review-checkpoints.md).

Call `start` only when no child is active. Invoke a non-null `delegate` with the
existing `task_tool_set`, omitting `resume`; do not append messages to an
older child. Both reviewer definitions apply 20 iterations and budget 1.5.
Wait for that child before issuing another review. Collect its returned
VRP event ID using the active `pair_id`; task success alone is insufficient.
Do not pass checkpoint files or earlier review prose to an independent child.

For a provider failure, exhausted limit, interrupted child or missing image,
wait until the native task has stopped, then `pause` with a reason. A pause
does not cancel a native task. At most two fresh attempts are available per
source/role. A running checkpoint after coordinator interruption needs
native child status checked before pausing; never launch overlapping children.
SDK/provider retries and cancellation stay with the SDK; add no retry loop.
On the next `start`, intact records written before interruption are recovered
before another attempt is spent. Recovery preserves the first reservation
boundary, rejects ambiguous evidence, and can finish with `delegate: null`.

After primary/blind collection, reconcile their event IDs with
`ux_record_reconcile` using your coordinator session. Only an intact
round-1 `disagree` allows the checkpoint's `tiebreak` action for that image.
Reconcile again after collecting it. Unresolved disagreement remains unknown.
`collected` means advisory records collected, not workflow or product acceptance.
