# Bounded design, liaison and domain collection

Use `ux_work_checkpoint` or the launcher's `work-checkpoint --json request.json`
to retain completed work across interruptions. The coordinator passes the returned
`delegate` brief to a fresh native OpenHands `task_tool_set` child. This tool
executes no task, solver, provider retry or SDK `resume`.

```json
{
  "action": "create",
  "checkpoint_id": "kettle-development",
  "session_id": "<native coordinator session ID>",
  "source_path": "requirements.json",
  "attempt_budget": 6,
  "steps": [
    {"id": "design", "kind": "design", "output_contract": "kettle.ux.json"},
    {
      "id": "sound", "kind": "liaison", "target_agent": "bard",
      "request_path": "liaison/sound.ux-request.json", "depends_on": ["design"]
    },
    {
      "id": "build", "kind": "domain", "target_agent": "firmware",
      "request_path": "liaison/build.ux-request.json", "depends_on": ["sound"]
    }
  ]
}
```

Every action requires the same checkpoint and native coordinator identity. A run
has one immutable attempt budget (default 24), at most two attempts per step and
one active child. Keep the same checkpoint for the same run: a different ID is
a separate scope, not an attempt-cap reset. Steps have unique IDs, are ordered,
and reference only earlier dependencies. Optional `inputs` name additional
workspace files or directories to hash. `source_path` remains unchanged for
the whole run; a design output must be separate from pinned inputs.
Inputs must exist. Use stable input directories outside checkpoint storage;
the workspace root and ancestors of `observations/ux/work-checkpoints/` are
rejected because saving a checkpoint would change their pinned contents.

Independent steps pin inputs at creation. Dependent steps pin them at first
start, after prerequisite outputs exist. Create requests through `ux_request`
before starting each liaison/domain step. They must reside in `liaison_dir`
(default `liaison`), match the planned target, and reference intact inputs.
Once pinned, changed or missing inputs block reuse and new starts.

| Action | Additional fields | Behavior |
| --- | --- | --- |
| `status` | None | Rehash inputs and collected evidence, rerun design/liaison validation; checkpoint bytes remain unchanged. |
| `start` | None | Reserve the next incomplete step; return its brief and attempt ID. Completed steps consume no further attempts. |
| `collect` | `step_id`, `attempt_id`, `child_session_id` | Verify the reserved attempt's evidence and bind it to a fresh native child identity. |
| `pause` | `step_id`, `attempt_id`, `reason`; optional `child_session_id` | Release the active reservation and retain a provider, cancellation, timeout, rate-limit or budget gap. No automatic retry. |

On interruption, inspect the native child before pausing or collecting its
reservation. `collect` can recover already-written evidence from the last
paused attempt without starting another child or consuming an attempt, even
when the budget is exhausted. It cannot recover a superseded attempt. A new
attempt must use a different child from every previous attempt and from the
coordinator. Native iteration/cost limits come from each loaded agent's
definition; SDK backoff/retry remains the SDK's responsibility. Optional
`reported_usage` (`native_iterations`, `cost_usd`) is coordinator-reported,
not verified provider accounting. Missing counters remain unknown.

The CLI exits 0 only when evidence is `collected`; pending, active, blocked and
error results exit 1, like the review collector. Inspect the JSON `status` and
`detail` rather than treating a reserved attempt as completed work.

A design step requires a valid output contract and current deterministic UX
gates. Liaison collection requires an intact `answered` response with status
`done`, completed request dependencies and at least one hashed artifact.
Domain collection additionally requires reported gate verdicts. Those reported
verdicts are evidence, not independently reproduced domain validation or proof
of native child execution. Referenced artifacts are workspace-relative,
including when requests live in a nested liaison directory.

Checkpoints live in `observations/ux/work-checkpoints/`. Process locks serialize
updates; atomic replacement and a SHA-256 seal detect partial writes and
accidental edits. The seal is a checksum, not authentication against a writer
who can replace files and recompute hashes. Blind reviewers cannot access this
coordinator tool, and direct generated-file edits are blocked by hooks.

`status: collected` means the declared evidence was collected. `acceptance`,
`workflow_completion` and `native_execution` remain `unknown`. Missing GUI,
perception, audio or hardware evidence is not supplied by this collector.
Use [review checkpoints](review-checkpoints.md) for independent image reviews.
