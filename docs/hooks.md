# Plugin hooks

Hook registration is in `plugins/ux/hooks/hooks.json`. Hooks add workspace
safety, environment checks, and evidence collection around an OpenHands
session. They do not replace the core schemas or deterministic gates.

## Event map

| Event and matcher | Hook names | Behavior |
| --- | --- | --- |
| `session_start` (`*`) | `ux-doctor`, `intake-attachments`, `ensure-llm-profiles`, `require-records` | Probe readiness, ingest any current attachments, ensure model profiles are usable, and load the record policy. |
| `user_prompt_submit` (`*`) | `intake-attachments` | Capture supported user-provided image attachments in the workspace. |
| `pre_tool_use` (`file_editor|apply_patch|terminal`) | `protect-generated` | Reject hand edits to generated outputs and unsafe generated-file writes. |
| `pre_tool_use` (`terminal`) | `safety-rail` | Reject dangerous shell operations in the workspace. |
| `stop` (`*`) | `require-records`, `report-ux-status`, `intake-attachments` | Check required records, summarize UX and image-review status, and finalize attachment intake. |
| `post_tool_use` (`inspect_image_with_vision`) | `record-vision-tool-event` | Record the vision-tool event so a later review can cite its event ID. |
| `post_tool_use` (`file_editor|ux_render|ux_author`) | `record-image-observation` | Capture applicable image observations after artifact authoring or rendering. |

## Hook scripts

| Script or helper | Responsibility |
| --- | --- |
| `ensure_llm_profiles.py` | Check or establish the configured author/reviewer model profiles. |
| `intake_attachments.py` | Copy supported attachment images into the workspace and invoke the intake path. |
| `protect_generated.py` | Guard generated contract projections from direct edits. |
| `record_image_observation.py` | Capture image observation evidence after relevant artifact tools. |
| `record_vision_tool_event.py` | Record post-tool vision events for later source-event binding. |
| `report_ux_status.py` | Summarize outstanding image reviews and UX status at stop. |
| `require_records.py` | Enforce the configured session/stop record policy and write its latest status. |
| `safety_rail.py` | Refuse dangerous terminal write patterns before execution. |
| `_records.py` | Shared helper for VRP event collection and serialization; do not fork from its canonical family version. |

The record policy is `plugins/ux/hooks/records-policy.json`. It directs agents
to `ux_record_decision`, `ux_record_impression`, and
`ux_record_vision_review`, or to the equivalent CLI `record` subcommand.
Impressions must contain at least 400 characters and three sentences and
should cover what was noticed, what works, what worries the team, how a maker
or user may read it, and what to do next. Policy artifact globs and ignored
paths are part of the checked-in JSON.

Stop enforcement is bounded: the policy allows at most two stop denials
before reporting the remaining status. It does not generate fabricated
decisions or impressions. The shared hook copies `_records.py` and
`require_records.py` are protected by the exact SHA-256 checks in
`scripts/check_shared_hooks.py`; update them only under the family-wide
change process.

## Failure handling

Hooks fail closed for protected writes and missing required records. A
best-effort image attachment or status hook may report that no action was
available; that is not evidence that a visual review passed. Consult the
session output and `observations/ux/records-status.json` when a hook denies a
stop.
