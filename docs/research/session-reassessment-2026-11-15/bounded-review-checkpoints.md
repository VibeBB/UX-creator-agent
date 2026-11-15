# D: bounded fresh-child review collection

The approved strategy reuses completed records only after revalidating
their source hashes and evidence, and gives unfinished image/reviewer
pairs fresh native children. This implements the image-review portion of
work package D in UX. It does not complete the broader product workflow.
The [initial validation](bounded-review-validation.json) and
[review-fix validation](bounded-review-followup-validation.json) identify
implementation commits, source digests, commands, log hashes and repeats.

## Implementation and scope

`ux_review_checkpoint` and `review-checkpoint --json` share the deterministic
collector in `src/ux_creator/review_checkpoint.py`. Checkpoints contain
contract/image paths and SHA-256, coordinator identity, reviewer roles,
bounded attempts and gap reasons, review event IDs, and any round-1
reconciliation authorizing a tiebreak. They contain no conversation history.
Atomic replacement and a process lock serialize checkpoint updates.

On every load, current sources and referenced VRP/image-delivery evidence
are checked again. Old records, another path, another checklist, another
coordinator, another reviewer role, missing files, malformed logs and
unverifiable delivery cannot become cached success. `status` preserves
checkpoint bytes and mtime. A checksum detects edits, but is not an
authentication mechanism against arbitrary filesystem writers.

`start` reserves one pair and returns a brief for existing SDK
`task_tool_set`, without `resume`. Primary precedes blind; at most one
pair is active in the checkpoint. Each source/checklist/role has two
fresh attempts. `pause` preserves failure reasons and attempt counts;
the coordinator must first establish that the native task has stopped.
Before another attempt, `start` recovers a unique intact record written
after that pair's first reservation. This also works after attempt two,
without consuming another attempt. Ambiguous records remain an error;
pre-reservation records remain ineligible. A completed recovery may return
`delegate: null`, which the coordinator must not launch as another child.
The collector neither launches nor cancels tasks and adds no provider
retry loop. Both shipped reviewer definitions use 20 native iterations
and budget 1.5. Budget checks occur after a step, so one call can exceed
the configured amount before the SDK stops the run.

Blind/tiebreak briefs carry source paths/hashes, checklist, role and an
opaque primary event ID. Previous prose and checkpoint paths stay out.
The blind guard rejects checkpoint CLI/MCP access, including prefixed
MCP tool names. Generated-file protection covers checkpoint writes.

Tiebreak creation requires an intact coordinator round-1 disagreement
whose metrics agree with recomputation from the referenced reviews.
The authorizing event ID is retained and revalidated after interruption.
A second unresolved round remains unknown. `collected` means requested
advisory records exist; acceptance is always `unknown`. Reconciliation,
deterministic gates, Stop permission and product acceptance remain separate.

## Validation

The final reviewed implementation passed all 805 tests in the fast stage,
including the configured structural coverage floors. Ruff, formatting,
Pyright, required image/hook/Stop regressions, docs verification and SDK
plugin loading also passed. Source was clean before and after the captured
run, and HEAD did not change during it.

Five independent focused runs each passed 50 tests: 35 checkpoint cases,
eight native-limit/failure cases, and seven delegated-context cases.
Checkpoint cases include stale or damaged evidence, interruption, attempt
caps, blind isolation, path/SHA/session/role mismatch, tampered authorizing
reconciliations and unresolved second-round disagreement. The original
793-test/38-focused-test snapshot remains unchanged; an intermediate fix
passed 803/48 before the final source-path isolation regression was added.

Review found and reproduced three additional boundary defects:

- A legitimate event-only native review lacked required image fields and
  prevented all checkpoint actions. Optional image fields retain sequence
  history while event-only records remain ineligible as image evidence.
- A child could write a valid independent review and fail before returning
  its ID. Replacing the sequence boundary on retry stranded that record
  while the writer correctly refused another same-role review. Recovery
  now revalidates it before another reservation, retaining the original
  boundary and prior failure reasons for every reviewer role.
- Recovery inspected unrelated review paths. A symlink at such a path
  aborted retries for another image. Unsafe candidate paths now produce
  a local evidence gap; they cannot complete a pair or stop unrelated work.
  Both matching-hash and different-hash cases are covered.

The eight native cases exercise `TaskExecutor` -> `TaskManager` ->
`LocalConversation.run()` for both shipped reviewer definitions. Synthetic
agent steps hit the actual 20-iteration bound, cross the native budget
gate through synthetic cost accounting, pause the child, or raise a
synthetic provider timeout. Each case creates two distinct fresh children,
preserves both gap reasons and refuses a third attempt. The shipped
SessionStart and blind pre-tool hooks run. No provider calls occur.
For isolation, reviewer model selection is inherited in memory and MCP
configuration is empty; these cases do not test real model profiles,
MCP-server startup, provider retry/backoff or live cancellation timing.

Development failures are preserved privately. Initial review fixtures
violated existing novelty/anchor rules; another fixture placed disagreement
only in facets although reconciliation compares finding categories. Native
test drafts incorrectly expected unconsumed SessionStart context and event
codes in returned error text, and initially registered synthetic metrics
twice. Fixtures were corrected against observed SDK/VRP behavior; the SDK
and production record requirements were not weakened. All checks on the
committed implementation passed. Follow-up fixture drafts also repeated
primary prose or named the wrong/missing claim anchor; their failures are
retained alongside the corrected behavioral regressions, rather than
reported as production regressions.

## Post-merge publication and launcher check

PR [#199](https://github.com/VibeBB/UX-creator-agent/pull/199) merged as
`ea08596ecd4ca1d2b2125c35f5f78883aa2ddc2a`. Its final head has 16 successful
checks. The merge has 15 successful checks and one skipped reconcile;
local fast verification again passed 805 tests, plugin loading passed,
and the focused suite passed 50 tests.

Image publication run
[43723462167](https://github.com/VibeBB/UX-creator-agent/actions/runs/43723462167)
completed successfully. Its automatically merged
[pin PR #200](https://github.com/VibeBB/UX-creator-agent/pull/200) changes
only the two image lock files. Verified provenance binds the published
image digest to the implementation merge above.

The shipped launcher passed prewarm/create/status/start/pause twice with
attestation required: first using the previous locked image and merge-source
overlay, then using the newly published image and only copied plugin assets.
The latter run asserted that source resolution returned `None`, preventing
host source from masking the baked package. Both preserved checkpoint bytes
and mtime on status, reserved one primary pair and retained attempt 1 after
pause. Uncollected states intentionally returned CLI exit code 1.

These were synthetic byte-identity checks with an empty JSON contract and
non-image fixture bytes. They launched no native child or provider and do
not establish product validity or visual review. Exact commits, digest,
commands and private-log hashes are recorded in the
[post-merge validation](bounded-review-post-merge-validation.json).

## Remaining boundaries

- Delivery references prove returned bytes and record consistency, not
  model perception. Native inspector source selection remains unknown.
- Attempt limits are scoped to one checkpoint/coordinator review run.
  Creating another checkpoint must not be used to reset the same run.
- Shared owner-policy consumption and crop/tile ancestry remain unfinished
  in C3. This collector does not implement those contracts.
- Design/liaison/domain-stage recovery, release-pinned clean installation
  and cooperation, missing feature-matrix cells, real GUI/audio/hardware
  behavior and product acceptance remain separate work.

Use the [operating guide](../../review-checkpoints.md) for action payloads.
The [native resume probe](sdk-native-review-limits.md) explains why this
path does not restore an old child. Complete private logs and synthetic
runtime identities stay in the evidence addendum, outside the public repo.
