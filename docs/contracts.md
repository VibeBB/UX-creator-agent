# Contract and artifact formats

The strict Pydantic models in `src/ux_creator/` define accepted JSON shapes.
Unknown properties are rejected. File paths are interpreted relative to the
workspace and must not escape it. Generated projections are outputs, not
alternate authored contracts.

## UX contract v1

The main artifact is `{product}.ux.json` with `schema_version: 1` and
`system: "ux-creator"`. Its authored sections capture:

| Section | What it describes |
| --- | --- |
| `product` and `surfaces` | Product identity, interface/physical surfaces, and declared controls. |
| `personas` | The people and contexts the experience serves. |
| `jobs` | Functional, emotional, and social Jobs-to-be-Done plus ODI served/opportunity values. |
| `journeys` | Stages, job links, surfaces, touchpoints, and experience/emotion observations. |
| `service_blueprint` | User actions, frontstage, backstage, and supporting service processes. |
| `statecharts` | States, initial/final semantics, events, transitions, guards, actions, entry and exit behavior. |
| `qcd` | Quality, cost, and delivery stance. |
| `feedback` and `loops` | Trigger/response modalities and action/reward cadence. |
| `imports` | Sister source paths, SHA-256 provenance, and extracted touchpoint candidates. |
| `controls` | Numeric or accessibility-relevant declared controls used by HIG checks. |
| `cmf` and `content` | Form/material/color/finish/marking plus LED, sound, haptic, motion, and text assets. |

The contract is validated with `load_contract`. `run_gates` checks only
declared data and its available evidence. Common outputs are written by
`write_projections` and `write_report`.

### Generated projections

`author` writes contract-derived journey and statechart Mermaid, statechart
PlantUML/XState/SCXML, wireframe and service-blueprint PlantUML, emotion
curve JSON/Mermaid, mind-map, sequence and WBS PlantUML, experience-loop
diagrams, ODI CSV, Storybook requirements, CMF/content maps, manifest,
provenance, and `ux-report.json` / `ux-report.md`. Exact projection names
depend on the authored product, journeys, and statecharts. `render` can add
SVG and PNG render outputs.

## Proposal and production files

- `{name}.ux-proposals.json` contains candidate changes, which deterministic
  QCD triage turns into a `.triage.json` result and eligible requests.
  High-risk items require a rationale citing a declared job ID; bold
  proposals also need a named theory break and underserved opportunity.
- `{product}.production.json` has `schema_version: 1`,
  `system: "ux-creator"`, and `artifact_kind: "ux_production_plan"`, plus
  product/revision/goal, optional contract path, workstreams, decisions,
  blockers, and evidence. Workstreams use the six product stages
  `requirements`, `design`, `manufacturing_handoff`, `build`, `evaluation`,
  and `revision`; statuses are `todo`, `in_progress`, `blocked`, and `done`.
- Production projections include status JSON/Markdown and a Mermaid plan.
  Status and diagrams are generated; author the plan file instead.

## SLP v2 request and response

Requests and responses are strict, frozen JSON records with
`schema_version: 2` and `system: "ux-creator"`. Request IDs and paths are
normalized workspace-relative references; hashes are lowercase 64-character
SHA-256 digests.

| Request field | Meaning |
| --- | --- |
| `id`, `target_agent`, `stage`, `risk` | Stable request ID, one of ten registered targets, product stage, and low/high risk. |
| `purpose`, `rationale`, `requested_changes` | Why the sister work is needed and what should change. |
| `inputs` | Paths and tree hashes captured when the request is created. |
| `expected_deliverables`, `acceptance` | Required outputs and how to decide whether they satisfy the request. |
| `depends_on`, `created_at` | Request dependencies and timezone-aware creation time. |

Responses use `request`, `responder`, `status`, `reason`, `input_hashes`,
`artifacts`, `gate_verdicts`, `decision_refs`, `impression_refs`,
`questions_for_user`, and timezone-aware `responded_at`. Statuses are
`accepted`, `in_progress`, `done`, `rejected`, `deferred`, and `needs_info`.
Statuses that represent a conclusion require a sufficiently detailed reason;
`done` cannot contain failing or unknown gate verdicts.

Differing request files are not overwritten unless the caller explicitly
sets `replace`. Identical writes are idempotent. See
[Sister cooperation](sister-cooperation.md) for the full exchange and state
reconciliation rules.

## VRP v1 records

The VibeBB Record Protocol uses append-only JSONL files under
`observations/ux/`. Each event carries `schema_version`, `kind`, `plugin`,
monotonic `sequence`, deterministic `event_id`, timezone-aware `recorded_at`,
and its kind-specific fields. File evidence is SHA-256 bound. The exact
decision, impression, and vision-review fields are documented in
[Records and vision](records-and-vision.md).

## Advisory records

Visual-review records use `review-visual-*.advisory.json`; image-intake
records use `intake-touchpoints-*.advisory.json`. Both bind observations to
image hashes. Malformed advisory files are surfaced in reconciliation output,
not accepted as valid evidence. Advisory status never changes a deterministic
gate verdict.
