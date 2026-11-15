# Review-boundary implementation follow-up

This supplements the historical [assessment](README.md) and
[implementation plan](implementation-plan.md). It describes source changes;
it does not upgrade the archived cooperative run to product acceptance.

## Native identity and review rounds

Record writers persist native session identity and reject a conflicting explicit
identity. An identity-free legacy record has a bounded timestamp fallback and
remains visibly uncertain. Independent reviews name one `primary_event_id`,
the same plugin, resolved image path and SHA-256, and a distinct reviewer session.
Copies at different resolved paths have separate rounds even with identical bytes.

Record-capable delegates declare identity-only `record-context` SessionStart
hooks. This avoids recalling earlier review prose into a blind review. Delegated
primaries also name their caller's native identity as `coordinator_session_id`;
that caller retains the independent-review and reconciliation obligations.

The offline SDK regression creates delegates through `TaskManager._create_task`
and executes the shipped SessionStart hooks. It checks distinct child identity
and absence of the parent's recall sentinel. Provider profiles and MCP startup
are replaced in memory for this check; no LLM judgment or GUI is exercised.

## Invalid record chains remain gaps

A coordinated primary plus a same-plugin reconciliation with `reviews: []`
previously reached an unchecked list index and raised `IndexError` during Stop.
The log validator reports invalid records alongside validation errors, so callers
must not treat every returned record as usable evidence.

Stop now quarantines a log with validation errors before review matching. It
retains the errors as compliance gaps, writes status, and applies the existing
bounded refusal policy. Empty, null and malformed reconciliation references are
covered by regressions. A corrupt log cannot supply completion evidence, even
when part of the chain remains parseable. The shared hook is synchronized across
all eleven plugins, with each repository's canonical digest guard updated.

## Blind reviewers return evidence to their caller

Workspace-wide Stop obligations conflicted with the blind guard: the reviewer
could not read a pending song to acknowledge it. Inspection receipts caused a
second dead end when a blind review had already been written without the opaque
inspection event ID, because the writer correctly rejects another review in the
same role and round.

Blind/tiebreak delegates therefore have no workspace-wide Stop hook. They still
retain their identity, blind guard, artifact protection and vision recording
hooks, and return one image-bound independent review to the caller. Primary-capable
delegates retain Stop enforcement. The caller still validates the bound review
and reconciliation; a missing blind review remains a caller-owned gap.

The SDK regression records an inspection through the child's real PostToolUse
hook and supplies a pending song. It checks that the blind guard still denies
reading the song, the blind delegate can stop, and the parent and primary-capable
delegate still receive song-receipt feedback.

An attempted alternative returned the inspection ID in PostToolUse
`additionalContext`. SDK 1.62.0 parses that field into hook diagnostics, but its
conversation hook processor does not inject PostToolUse context into model
messages. That alternative was removed before publication. Hook stdout alone
is not proof that the agent received context. A future receipt API must establish
its delivery boundary explicitly rather than expose earlier review logs.

The document plugin's published strict `vision_review` MCP schema also includes
`coordinator_session_id`, matching the writer's delegated-primary requirement.

## Committed-source verification

The [revision-bound verification matrix](review-boundary-validation.json) records
the eleven validated source revisions, runtime-file SHA-256 values, actual tool
versions, commands, exit codes, durations and private log filenames. All eleven
repositories passed their full fast/unit checks, lint, formatting, type checks,
shared-hook/workflow checks, documentation checks and SDK plugin load. Each
repository also passed its focused Stop suite five consecutive times (55 suite
runs). UX additionally passed both actual SDK delegated-startup cases.

The simulation verifier rejected the shared runner's unsupported `--jobs`
argument before executing checks. Its unchanged committed source then passed
the supported `--stage fast` command. The failed invocation is retained beside
the successful retry; it is not rewritten as a pass.

Raw logs remain private. The matrix describes the pinned source revisions;
later documentation-only evidence commits do not change those runtime files.
CI outcomes remain separately visible on each linked PR, and neither local
verification nor CI completion establishes product acceptance.

## Remaining acceptance boundaries

Image ownership, source-image hashes and crop/tile lineage still require the C3
recording contract. Finite orchestration budgets, serialized blind review,
resumable checkpoints and workflow-level completion remain work package D.
The existing per-session Stop refusal budget is not a workflow budget.

SDK startup, plugin loading, lint, type checks and deterministic regressions do
not establish released-image compatibility, real audio quality, hardware or
physical-device behavior, GUI operation, or LLM review quality. Stop permission,
record compliance, run completion and acceptance remain separate states.
