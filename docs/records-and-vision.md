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

## Session-scoped Stop status

The Stop hook excludes a record with an explicit different session ID,
even when its timestamp is recent. Legacy records without an ID are
eligible only from the session start through the following 24 hours;
their use is reported as an attribution warning. Missing session
identity or a missing start marker also leaves attribution unverified.
Reviews bind both the resolved image path and its SHA-256; an event ID
cannot substitute for that binding. Supply an explicit `image_path` to
the review writer so it records the current bytes. Legacy reference-only
reviews remain readable but do not discharge image-review obligations.

Stop writes `observations/<plugin>/records-status.json` and a
`observations/<plugin>/.sessions/<session>.status.json` snapshot:

| Field | Meaning |
| --- | --- |
| `stop_permission` | `deny` while the configured refusal budget remains, then `allow` |
| `record_compliance` | `fail` for missing evidence, `unknown` for attribution warnings, otherwise `pass` |
| `run_completion` | `unknown`; only the execution workflow can establish completion |
| `acceptance` | `unknown`; only the product acceptance workflow can establish it |
| `checkpoint` | Session marker containing the start time and refusal count |

An exhausted refusal budget permits termination while preserving the
unresolved problems. The compatibility `verdict` describes the hook's
problem list only; consumers must use the explicit fields above and must
not infer product acceptance from Stop permission or the absence of
record problems. Reviewer identity propagation and derived-image
ownership require a separate recording contract; this status does not
claim to verify them.

## Session attribution

Pass the native `session_id` from the SessionStart record context in record-tool
inputs. The writer also accepts `OPENHANDS_SESSION_ID` when supplied by the SDK
process; conflicting explicit and environment identities are rejected. The ID is
included in the record hash. Writers never infer it from shared marker files.

Delegate independent reviews with an opaque `primary_event_id`, the resolved image
path and SHA-256; never send the earlier findings. Reviewers keep their own native
`session_id`. The writer and Stop resolve that reference into an intact primary
with the same plugin, path and hash and a different native session. Every review
role has its own session. Reconciliation belongs to the primary's session.

A copied image has its own round. Historical inputs without identity remain
supported, with bounded timestamp attribution and an unknown compliance warning
at Stop; they cannot satisfy explicitly scoped writer rounds.

Stop permission, record compliance, run completion and acceptance are separate
status fields. Reaching the refusal budget permits stopping while preserving gaps;
it does not establish execution completion or product acceptance.
