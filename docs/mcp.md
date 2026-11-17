# MCP tools

The plugin exposes a stdio MCP server named `ux`. Its schemas and tool
descriptions are defined in `src/ux_creator/mcp_server.py`. All tools reject
unknown input keys. Paths are workspace-relative where the operation accepts a
workspace; the server validates paths before reading or writing.

| Tool | Inputs | Reads and writes | Result |
| --- | --- | --- | --- |
| `ux_work_checkpoint` | `action`, `checkpoint_id`, coordinator `session_id`; create source/steps/budget, collect step/attempt/child IDs, or pause reason. | Pins workspace inputs, validates design/SLP evidence, maintains `observations/ux/work-checkpoints/`. | Finite step/attempt state and fresh native-task brief; execution and acceptance stay unknown. |
| `ux_review_checkpoint` | `action`, `checkpoint_id`, coordinator `session_id`; action-specific contract/sources, pair/event IDs or pause reason. | Hashes sources, verifies VRP/image evidence, maintains `observations/ux/review-checkpoints/`. | Record-collection status, gaps, pair attempts, fresh-task brief; acceptance stays unknown. |
| `ux_record_decision` | VRP decision fields: `id`, `stage`, `question`, `principles`, `options`, `chosen`, `rationale`, `risks`, `revisit_when`, and `evidence`; optional assumptions/unknowns/decided_by. | Reads and hashes cited workspace evidence; appends to `observations/ux/decisions.jsonl`. | `verdict`, log path, validated event. |
| `ux_record_impression` | `stage`, artifact paths, and long-form `impression`. | Reads and hashes artifact files/directories; appends to the stage-impression log. | `verdict`, log path, event. |
| `ux_record_vision_review` | Image path or source event ID, model, checklist, findings, and impression. | Reads and hashes an image when supplied; appends to the vision-review log. | `verdict`, log path, event. |
| `ux_records_status` | No arguments. | Reads VRP logs and the latest stop-hook status. | Counts by record kind and `last_stop`; informational only. |
| `ux_record_reconcile` | `ReconcileInput`: image path and the primary/blind(/tiebreak) event ids. | Appends to `reconciles.jsonl`. | Deterministic agreement of independent vision reviews; a round-2 split is `unresolved` (unknown). |
| `ux_record_insight` | `InsightStatusInput`: insight ref, status, gate/decision refs, reason. | Appends to `insights.jsonl`. | Adopted needs a gate pass and a decision; rejected insights need `revisits` and new evidence. |
| `ux_record_song_receipt` | `SongReceiptInput`: song path and sha256, feeling, look-again flag. | Appends to `song-receipts.jsonl`. | Receipt for a bard song; never feeds a gate and never asks for another song. |
| `ux_record_read` | `ReadInput`: sister artifact path and producer. | Appends to `reads.jsonl`. | Resolves sister impressions bound to those bytes; the next impression must answer each ref. |
| `ux_records_digest` | No arguments. | Reads every `observations/*` log. | Family-wide integrity, open concerns, disputes, unanswered reads, insights, review splits and songs. |
| `ux_records_escalate` | No arguments. | Reads every `observations/*` log through the digest. | Draft `requests[]` (`target`, `requested_changes`, `upstream`) and `ecr_candidates[]` from unresolved error-level concerns; advisory, writes nothing. `production.error_concerns` stays `unknown` until they are resolved. |
| `ux_records_hub` | No arguments. | Reads every `observations/*` log through the digest. | Per-sister concern/dispute/read/insight/review-split counts, concern cycles between sisters, undelivered songs; `status` is `clear` or `attention`, advisory only. |
| `ux_records_search` | Optional query, system, kind, stage, artifact, severity, open_only, limit. | Reads every intact plugin log. | Keyword search over sister impressions; broken logs are listed separately. |
| `ux_doctor` | No arguments. | Probes the local environment. | Tool readiness checks. |
| `ux_validate_contract` | `contract` JSON object. | Validates in memory; no file write. | `verdict: pass` or `fail` and stage/detail. |
| `ux_gates` | Required `contract_path`; optional `workspace`. | Reads the contract and referenced workspace evidence. | Gate checks, verdict, and summary. |
| `ux_author` | Required `contract_path`, `out_dir`; optional `workspace`, `liaison_dir`, `render`. | Reads the contract and selected workspace evidence; writes projections, provenance, report, and optional images. | Gate/report payload; rendering may also return image content blocks. |
| `ux_from_ruby` | `source` and output path `out`. | Executes the UX Ruby DSL through the bridge; writes validated contract JSON. | `verdict`, stage, output contract path. |
| `ux_import` | `contract_path`, `system` (`circuit`, `mech`, `wire`, `bard`, or `csv`), and `file`. | Reads source; updates authored contract import provenance. | `verdict` and imported references. |
| `ux_request` | Required contract, request ID, target, stage, risk, purpose, changes, deliverables, and acceptance; optional rationale, input paths, dependencies, workspace, liaison directory, and `replace`. | Reads and hashes inputs; writes a request only if absent, identical, or explicitly replaced. | Request path and deterministic `delegate` brief. |
| `ux_delegate` | Required `request_id`; optional `workspace` and `liaison_dir`. | Reads and validates the request. | Request path and task-tool brief. |
| `ux_propose` | `contract_path`, `proposals_path`, and `out_dir`. | Reads contract/proposals; writes triage and eligible v2 requests. | Written paths and IDs held from automatic sending. |
| `ux_mruby_check` | `source` path. | Runs the pinned mruby syntax checker. | `verdict` and detail; missing tool is a failure, not an assumed pass. |
| `ux_review_reconcile` | `contract_path`, `out_dir`; optional `workspace`. | Reads contract, gates, and review advisory files. | Reconciled findings and malformed paths; findings do not change the gate verdict. |
| `ux_produce` | `plan_path`, `out_dir`; optional workspace, liaison directory, and `render`. | Reads the plan, contract, liaison responses, and workspace evidence; writes production status/projections and optional renders. | Production checks, hashed plan, written paths, and optional render results. |
| `ux_change_check` | Required `eco_path`; optional `workspace`. | Reads the ECO, its pinned ECR, changed files, gate reports and every workspace JSON pin. | Closure checks (`eco.*`, `dr.*`) and verdict. |
| `ux_liaison_status` | Optional `workspace`, `liaison_dir`, and `attach_images`. | Reads requests, responses, referenced inputs/artifacts, and VRP event references. | Entries, seven-state summary, malformed/orphan files; optional image content. |
| `ux_intake_reconcile` | `contract_path` and `out_dir`. | Reads contract and intake advisory files. | Declared, undeclared, unobserved, mismatched touchpoints, and malformed paths. |
| `ux_render` | `dir`. | Reads top-level Mermaid and PlantUML sources; writes SVG/PNG files. | Per-render status; image content blocks for successful renders. |

`ux_record_decision`, `ux_record_impression`, and
`ux_record_vision_review` append records and therefore advertise
`idempotentHint: false`. File-mutating tools, including `ux_render`, advertise
`readOnlyHint: false`; all tools advertise `destructiveHint: false`. These
annotations describe the tool's expected behavior, not permission to bypass
workspace safeguards.

`ux_review_checkpoint` also advertises `idempotentHint: false`: `start`
consumes a finite attempt. Only its `status` action is read-only. It is a
coordinator tool, denied to blind reviewers. See
[bounded review collection](review-checkpoints.md) for action inputs and
the distinction between collected records and accepted work.

`ux_work_checkpoint` has the same mutation annotations. See
[bounded work collection](work-checkpoints.md) for design, liaison and domain
steps, recovery, shared attempt budgets and evidence limitations.

## Outputs and errors

Ordinary results are JSON text with a `verdict`, stage, and operation-specific
fields. A handled validation or gate problem is returned as a `fail` payload.
Unknown tool names and uncaught operation errors use MCP's error result with
`isError: true`; the payload includes the tool name, detail, and exception
type. Missing render or Ruby tools remain explicit `unknown`/failure results.
No tool can make an advisory vision record into a gate pass.

Input schemas are the protocol source of truth. This table is a human index;
inspect `tool_specs()` or MCP's `tools/list` response for the precise JSON
Schema and annotations. `tests/test_mcp_server.py` checks descriptions,
annotations, read/write safety, and round trips.

## Inline image identity

`ux_render`, `ux_author`, `ux_produce`, and `ux_liaison_status` return
`inline_images` metadata alongside any attached PNG/JPEG content. An
`image_identity` contains a resolved image `path`, its producer's `sha256`,
`owner_plugin`, and `origin` (`renderer` or `liaison-response`). UX renderers
capture this identity after producing each output. Liaison attachments use
the strict SLP response's responder and artifact SHA. Its complete validated
content is checked against the scanned entry's `response_sha256`, including
artifacts, inputs and gate evidence. Ownership never comes from a path fragment.

`sha256` at the top of each entry hashes the bytes actually read for the
response. `identity_status` is `bound` only when that digest and the resolved
path match the producer's identity. A `mismatch` suppresses the attachment
and reports `reason: source_identity_mismatch`. Missing producer identity
remains `unknown`; a legacy image may still be attached for inspection.
Always check `identity_status` before using the claimed owner or revision.

`attached` reports delivery separately: a bound image may exceed the
4 MiB or eight-image cap. Binding proves neither that the model inspected
the image nor that its review was accepted. This metadata describes the
returned image; original-image ancestry for crops/tiles and downstream
review-record/Stop integration remain separate work.

The image-observation hook checks actual inline bytes against attachment
metadata and preserves the producer claim and observer session. Text-only
paths and withheld images do not count as delivered images. Returned-byte
hashes survive later file rewrites; unassociated bytes retain an unknown
identity and a null path. See the [observation boundary research](research/session-reassessment-2026-11-15/image-observation-delivery.md).
