# Records and vision

UX agent reasoning should leave a trace that a teammate can inspect after the
conversation. VibeBB Record Protocol (VRP) v1 provides append-only,
evidence-bound UX decisions, stage impressions, and vision reviews.

## Record locations and envelope

The plugin stores JSON Lines under `observations/ux/`:

| File | Record kind |
| --- | --- |
| `decisions.jsonl` | `decision` |
| `impressions.jsonl` | `stage_impression` |
| `vision-reviews.jsonl` | `vision_review` |
| `records-status.json` | Latest stop-hook policy result; informational status, not an event log. |

Each record has `schema_version: 1`, `plugin: "ux"`, a 1-based per-file
`sequence`, a deterministic SHA-256 `event_id`, and timezone-aware
`recorded_at`. Logs are append-only. Event IDs are used by sister responses
to cite decision or impression evidence.

## Decisions

A decision requires a stable ID, stage, question, at least one cited
principle, two or more named options, the chosen option, a reasoned rationale,
risks, and a condition for revisiting the choice. Assumptions and unknowns
are explicit lists; `decided_by` distinguishes agent from user decisions.
Option names must be unique and `chosen` must match one.

Evidence must contain a workspace file or directory path that the writer can
hash, or a non-file reference such as a standard, datasheet, or law. File
evidence is stored with a tree SHA-256 digest.

## Stage impressions

An impression binds a named stage and its resulting files/directories to a
prose reflection. The policy requires at least 400 characters and at least
three sentences. The reflection should say what was noticed, what works,
what is worrying, how a maker or user may read the result, and the next
action. Artifact tree hashes preserve the state being reflected on.

Use a completed stage rather than a vague session label. Record meaningful
contradictions and unknowns; the impression is not a substitute for a
decision record or a gate result.

## Vision reviews

A VRP vision review must bind to either an image path or a source vision
event ID and include the model, checklist, findings, and prose impression.
When an image path is provided, its SHA-256 is captured. Findings use
`category`, `severity` (`info`, `warning`, or `error`), and a note.

The image review path is separate from deterministic gates:

1. `record-vision-tool-event` captures the source event from the image
   inspection tool when one is available.
2. `ux-review` inspects a rendered artifact and writes a
   `review-visual-*.advisory.json` record with image path/hash, checklist,
   model, summary, and typed findings.
3. `review-reconcile` compares findings with authored contract and gate
   truth as `corroborated`, `contradicted`, or `unverifiable`.
4. The team chooses whether to revise the contract and rerun gates.

Review checklists include `journey_map`, `statechart`, `wireframe`,
`intake_image`, `service_blueprint`, `emotion_curve`, `production_plan`, and
`sister_artifact`. An explicit not-applicable record is available when no
vision-capable review could be performed. Missing or malformed reviews do not
become a pass.

## Image intake

When a workspace receives an image attachment, the intake path can preserve
the file and record touchpoint candidates with evidence, confidence, and an
optional surface. The image hash identifies the reviewed source. Intake
reconciliation reports declared, undeclared, unobserved, surface-mismatched,
and malformed items; it does not automatically add a candidate to the UX
contract.

## CLI and MCP

Use `ux_record_decision`, `ux_record_impression`,
`ux_record_vision_review`, and `ux_records_status` through MCP, or use
`python -m ux_creator record decision|impression|vision-review --json
<payload.json>` and `python -m ux_creator record status`. Image reviews can
also be written with `review-record` and compared with
`review-reconcile`. See [MCP](mcp.md) and [Commands](commands.md).
