# Bounded work-evidence collection

## Result and scope

The [work collector](../../work-checkpoints.md) extends the bounded review
pattern to ordered design, liaison and domain steps. Implementation revision
`6ed1c2d8f18475d11a52105b8e959da7692031e3` is proposed in
[PR #205](https://github.com/VibeBB/UX-creator-agent/pull/205). The
[validation record](bounded-work-validation.json) preserves commands, tool
versions, source hashes, log hashes and failed development attempts.

The collector pins the run source, step inputs, request target, dependencies,
response and artifact hashes. Dependent inputs are pinned only when the step
starts. It revalidates collected evidence before reuse. A design contract must
pass current UX gates; a domain response must retain reported gate verdicts.
Reported sister verdicts do not prove independent domain execution.

One child reservation, two attempts per step and an immutable shared attempt
budget bound collection. The coordinator receives a fresh native task brief;
the collector runs no child, provider request, custom retry or SDK resume.
Explicit pauses preserve timeout, cancellation, rate-limit and budget gaps.
The last paused attempt can collect evidence already written before interruption,
including after budget exhaustion, without reserving a third child.

Atomic replacement and process locks protect updates. The SHA seal detects
accidental corruption; it is not authentication against a writer that can
replace the file and recompute the checksum. Native child identities and usage
counters are coordinator-reported. Native execution remains unknown.

## Verification

- Fast verification passed: Ruff, formatting, strict Pyright, 874 tests
  (one skipped), shared hooks, documentation and whitespace checks.
- All seven agent definitions loaded through the pinned OpenHands SDK.
- The work collector and native reviewer-limit probes passed five repetitions
  on the implementation commit. These cover interrupted collection, attempt
  exhaustion, changed source/contract/input/response/artifact evidence,
  nested liaison paths, atomic-write failure and competing processes.
- Native SDK tests exercise hook dispatch and synthetic iteration, budget,
  pause and timeout failures. They do not call a live model provider.

The SDK test caught a real hook-registration omission: updating the blind guard
function alone did not register the new MCP tool in the agent's matcher. The
matcher now covers both review and work checkpoint tools, including namespaced
names, and terminal access remains denied. Failed fast-verification attempts
also caught the command-documentation inventory omission. Neither failure is
counted as a successful verification run.

## Acceptance boundary

`collected` means that declared evidence was collected and revalidated.
Product acceptance, workflow completion, model perception and native execution
remain unknown. The tests use synthetic SLP fixtures and explicit reported
verdicts, not a new eleven-plugin product-development run.

The published-image clean installation, full domain readback matrix,
doctor/prewarm improvements and public-claim audit remain separate work packages.
This collector does not satisfy missing GUI, audio, WASM, hardware or native
image-selection evidence.
