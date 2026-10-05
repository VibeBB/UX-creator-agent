# MCP tools

The plugin exposes a stdio MCP server named `ux`. Its schemas and tool
descriptions are defined in `src/ux_creator/mcp_server.py`. All tools reject
unknown input keys. Paths are workspace-relative where the operation accepts a
workspace; the server validates paths before reading or writing.

| Tool | Inputs | Reads and writes | Result |
| --- | --- | --- | --- |
| `ux_record_decision` | VRP decision fields: `id`, `stage`, `question`, `principles`, `options`, `chosen`, `rationale`, `risks`, `revisit_when`, and `evidence`; optional assumptions/unknowns/decided_by. | Reads and hashes cited workspace evidence; appends to `observations/ux/decisions.jsonl`. | `verdict`, log path, validated event. |
| `ux_record_impression` | `stage`, artifact paths, and long-form `impression`. | Reads and hashes artifact files/directories; appends to the stage-impression log. | `verdict`, log path, event. |
| `ux_record_vision_review` | Image path or source event ID, model, checklist, findings, and impression. | Reads and hashes an image when supplied; appends to the vision-review log. | `verdict`, log path, event. |
| `ux_records_status` | No arguments. | Reads VRP logs and the latest stop-hook status. | Counts by record kind and `last_stop`; informational only. |
| `ux_doctor` | No arguments. | Probes the local environment. | Tool readiness checks. |
| `ux_validate_contract` | `contract` JSON object. | Validates in memory; no file write. | `verdict: pass` or `fail` and stage/detail. |
| `ux_gates` | Required `contract_path`; optional `workspace`. | Reads the contract and referenced workspace evidence. | Gate checks, verdict, and summary. |
| `ux_author` | Required `contract_path`, `out_dir`; optional `render`. | Reads the contract; writes projections, provenance, report, and optional images. | Gate/report payload; rendering may also return image content blocks. |
| `ux_from_ruby` | `source` and output path `out`. | Executes the UX Ruby DSL through the bridge; writes validated contract JSON. | `verdict`, stage, output contract path. |
| `ux_import` | `contract_path`, `system` (`circuit`, `mech`, `wire`, `bard`, or `csv`), and `file`. | Reads source; updates authored contract import provenance. | `verdict` and imported references. |
| `ux_request` | Required contract, request ID, target, stage, risk, purpose, changes, deliverables, and acceptance; optional rationale, input paths, dependencies, workspace, liaison directory, and `replace`. | Reads and hashes inputs; writes a request only if absent, identical, or explicitly replaced. | Request path and deterministic `delegate` brief. |
| `ux_delegate` | Required `request_id`; optional `workspace` and `liaison_dir`. | Reads and validates the request. | Request path and task-tool brief. |
| `ux_propose` | `contract_path`, `proposals_path`, and `out_dir`. | Reads contract/proposals; writes triage and eligible v2 requests. | Written paths and IDs held from automatic sending. |
| `ux_mruby_check` | `source` path. | Runs the pinned mruby syntax checker. | `verdict` and detail; missing tool is a failure, not an assumed pass. |
| `ux_review_reconcile` | `contract_path`, `out_dir`; optional `workspace`. | Reads contract, gates, and review advisory files. | Reconciled findings and malformed paths; findings do not change the gate verdict. |
| `ux_produce` | `plan_path`, `out_dir`; optional workspace, liaison directory, and `render`. | Reads the plan, contract, liaison responses, and workspace evidence; writes production status/projections and optional renders. | Production checks, hashed plan, written paths, and optional render results. |
| `ux_liaison_status` | Optional `workspace`, `liaison_dir`, and `attach_images`. | Reads requests, responses, referenced inputs/artifacts, and VRP event references. | Entries, seven-state summary, malformed/orphan files; optional image content. |
| `ux_intake_reconcile` | `contract_path` and `out_dir`. | Reads contract and intake advisory files. | Declared, undeclared, unobserved, mismatched touchpoints, and malformed paths. |
| `ux_render` | `dir`. | Reads top-level Mermaid and PlantUML sources; writes SVG/PNG files. | Per-render status; image content blocks for successful renders. |

`ux_record_decision`, `ux_record_impression`, and
`ux_record_vision_review` append records and therefore advertise
`idempotentHint: false`. File-mutating tools, including `ux_render`, advertise
`readOnlyHint: false`; all tools advertise `destructiveHint: false`. These
annotations describe the tool's expected behavior, not permission to bypass
workspace safeguards.

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
